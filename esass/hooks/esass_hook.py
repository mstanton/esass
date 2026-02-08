#!/usr/bin/env python3
"""
ESASS Hook for Claude Code

Captures tool calls from Claude Code and logs them to ESASS.
Configure in ~/.claude/hooks.json to enable automatic observation.

Setup:
    Add to ~/.claude/hooks.json:
    {
      "hooks": {
        "PostToolUse": [{
          "command": "python /path/to/esass_hook.py",
          "timeout": 5000
        }]
      }
    }
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import hashlib
import pickle  # for persistent state if needed
from typing import Any, Dict, List, Optional

# Add parent to sys.path to allow importing esass core
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from esass.probes.config import ESASSProbeSystemConfig, create_default_probes
    from esass.probes.registry import ProbeRegistry
    from esass.probes.base import ProbeContext

    PROBES_AVAILABLE = True
except ImportError:
    PROBES_AVAILABLE = False

# ESASS data directory
# ESASS data directory
ESASS_DATA_DIR = Path(
    os.environ.get("ESASS_DATA_DIR", str(Path.home() / ".esass" / "data"))
)


def ensure_data_dir():
    """Ensure data directory exists."""
    ESASS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (ESASS_DATA_DIR / "logs").mkdir(exist_ok=True)
    (ESASS_DATA_DIR / "state").mkdir(exist_ok=True)
    (ESASS_DATA_DIR / "patterns").mkdir(exist_ok=True)
    (ESASS_DATA_DIR / "skills").mkdir(exist_ok=True)


def get_session_id():
    """Get or create today's session ID."""
    state_file = ESASS_DATA_DIR / "state" / "current_session.json"
    today = datetime.now().strftime("%Y%m%d")

    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                if state.get("date") == today:
                    return state.get("session_id")
        except:
            pass

    # Create new session
    session_id = (
        f"session_{today}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
    )
    ensure_data_dir()
    with open(state_file, "w") as f:
        json.dump({"date": today, "session_id": session_id}, f)

    return session_id


def extract_context(tool_name: str, params: dict) -> dict:
    """Extract semantic context from tool call."""
    context = {"category": "unknown", "target": None, "action": None, "tags": []}

    # Categorize by tool
    if tool_name in ["Read", "Write", "Edit"]:
        context["category"] = "file_operation"
        context["target"] = params.get("file_path", "")
        context["action"] = tool_name.lower()

        # Extract file type
        if context["target"]:
            ext = Path(context["target"]).suffix.lower()
            if ext:
                context["tags"].append(f"filetype:{ext}")

            # Detect common patterns
            path_lower = context["target"].lower()
            if "test" in path_lower:
                context["tags"].append("testing")
            if "config" in path_lower or ext in [".json", ".yaml", ".yml", ".toml"]:
                context["tags"].append("configuration")
            if "__init__" in path_lower:
                context["tags"].append("module_init")

    elif tool_name in ["Grep", "Glob"]:
        context["category"] = "search"
        context["action"] = "search"
        context["target"] = params.get("pattern", params.get("query", ""))
        context["tags"].append("codebase_exploration")

    elif tool_name == "Bash":
        context["category"] = "command"
        cmd = params.get("command", "")
        context["target"] = cmd[:100]

        # Detect command types
        if cmd.startswith("git "):
            context["tags"].append("git")
            if "commit" in cmd:
                context["action"] = "commit"
            elif "push" in cmd:
                context["action"] = "push"
            elif "pull" in cmd or "fetch" in cmd:
                context["action"] = "sync"
            elif "status" in cmd or "diff" in cmd or "log" in cmd:
                context["action"] = "inspect"
        elif cmd.startswith("pytest") or cmd.startswith("python -m pytest"):
            context["tags"].append("testing")
            context["action"] = "test"
        elif cmd.startswith("pip ") or cmd.startswith("npm "):
            context["tags"].append("package_management")
            context["action"] = "install" if "install" in cmd else "package_op"
        elif "docker" in cmd:
            context["tags"].append("containerization")

    elif tool_name == "Task":
        context["category"] = "delegation"
        context["action"] = "spawn_agent"
        context["target"] = params.get("subagent_type", "unknown")
        context["tags"].append(f"agent:{context['target']}")

    elif tool_name in ["WebFetch", "WebSearch"]:
        context["category"] = "web"
        context["action"] = "fetch" if tool_name == "WebFetch" else "search"
        context["target"] = params.get("url", params.get("query", ""))
        context["tags"].append("external_resource")

    return context


def log_event(event_type: str, data: dict):
    """Append event to daily log file."""
    ensure_data_dir()

    today = datetime.now().strftime("%Y%m%d")
    log_file = ESASS_DATA_DIR / "logs" / f"log_{today}.jsonl"

    entry = {
        "event_id": hashlib.md5(
            f"{datetime.now().isoformat()}{event_type}{json.dumps(data)}".encode()
        ).hexdigest()[:16],
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "session_id": get_session_id(),
        "event_data": data,
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry["event_id"]


def update_sequence_state(tool_name: str, context: dict):
    """Track tool sequences for pattern detection."""
    state_file = ESASS_DATA_DIR / "state" / "sequence_state.json"

    try:
        if state_file.exists():
            with open(state_file, "r") as f:
                state = json.load(f)
        else:
            state = {"recent_tools": [], "sequences": {}}

        # Add to recent tools (keep last 10)
        state["recent_tools"].append(
            {
                "tool": tool_name,
                "category": context["category"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        state["recent_tools"] = state["recent_tools"][-10:]

        # Track 2-tool and 3-tool sequences
        tools = [t["tool"] for t in state["recent_tools"]]
        if len(tools) >= 2:
            seq2 = f"{tools[-2]} -> {tools[-1]}"
            state["sequences"][seq2] = state["sequences"].get(seq2, 0) + 1
        if len(tools) >= 3:
            seq3 = f"{tools[-3]} -> {tools[-2]} -> {tools[-1]}"
            state["sequences"][seq3] = state["sequences"].get(seq3, 0) + 1

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    except Exception:
        pass  # Don't fail on state tracking errors


class CapturePipeline:
    """Simple pipeline to capture probe entries in-process."""

    def __init__(self):
        self.entries = []

    def submit(self, entries):
        self.entries.extend(entries)


def main():
    """Process hook input from Claude Code."""
    ensure_data_dir()

    # Initialize Probes if available
    registry = None
    capture_pipeline = CapturePipeline()
    state_file = ESASS_DATA_DIR / "state" / "probe_state.pkl"

    if PROBES_AVAILABLE:
        # Try to load existing registry from pickle
        if state_file.exists():
            try:
                with open(state_file, "rb") as f:
                    registry = pickle.load(f)
                    # Restore transient pipeline
                    registry.event_pipeline = capture_pipeline
            except:
                registry = None

        # Create new if loading failed
        if registry is None:
            try:
                config = ESASSProbeSystemConfig()
                config.data_dir = str(ESASS_DATA_DIR)
                probes = create_default_probes(config)
                registry = ProbeRegistry()
                registry.event_pipeline = capture_pipeline
                for probe in probes:
                    registry.register(probe)
            except Exception:
                registry = None

    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            return

        hook_data = json.loads(input_data)

        # Extract fields from Claude Code hook
        tool_name = hook_data.get("tool_name", "unknown")
        tool_input = hook_data.get("tool_input", {})
        tool_output = hook_data.get("tool_output", "")
        # Claude Code results often indicate success/failure
        success = hook_data.get("success", True)
        error = hook_data.get("error")
        session_id = get_session_id()

        if not tool_name or tool_name == "unknown":
            return

        # 1. Notify Probes (Meta-cognitive analysis)
        if registry:
            # Notify of tool completion (Claude hook runs after tool use)
            event_data = {
                "tool_name": tool_name,
                "parameters": tool_input,
                "result": str(tool_output)[:1000],
                "success": success,
                "error": error,
            }

            # Use same timestamp for consistency
            ts = datetime.now()

            # We notify both start (reconstructed) and complete to trigger all probes
            # ToolCallProbe and ReliabilityProbe listen to completion/error
            registry.notify(
                "tool_call_start",
                {
                    "tool_name": tool_name,
                    "parameters": tool_input,
                    "call_id": "hook-last",
                },
                {"session_id": session_id, "timestamp": ts},
            )

            # Capture probe observations (now via pipeline)
            registry.notify(
                "tool_call_complete" if success else "tool_call_error",
                event_data,
                {"session_id": session_id, "timestamp": ts},
            )

            # Log any meta-cognitive observations (alerts, boundary actions, etc.)
            if capture_pipeline.entries:
                for obs in capture_pipeline.entries:
                    log_entry_object(obs)

        # 2. Standard Context Extraction (Legacy support for simple dashboards)
        context = extract_context(tool_name, tool_input)

        # 3. Log the primary tool event
        log_data = {
            "tool_name": tool_name,
            "parameters": tool_input,
            "result_preview": str(tool_output)[:500] if tool_output else None,
            "context": context,
            "success": success,
            "error": error,
        }
        log_event("tool_call", log_data)

        # 4. Update sequence tracking
        update_sequence_state(tool_name, context)

        # 5. Persist probe state
        if registry:
            try:
                # Remove non-pickleable pipeline reference
                registry.event_pipeline = None
                with open(state_file, "wb") as f:
                    pickle.dump(registry, f)
            except Exception as pe:
                try:
                    debug_log = ESASS_DATA_DIR / "logs" / "hook_debug.log"
                    with open(debug_log, "a", encoding="utf-8") as f:
                        f.write(
                            f"[{datetime.now().isoformat()}] Pickle Error: {str(pe)}\n"
                        )
                except:
                    pass

    except Exception as e:
        try:
            debug_log = ESASS_DATA_DIR / "logs" / "hook_debug.log"
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(
                    f"[{datetime.now().isoformat()}] Error in hook main: {str(e)}\n"
                )
            log_event("hook_error", {"error": str(e)})
        except:
            pass


def log_entry_object(entry):
    """Log a LogEntry object directly."""
    today = datetime.now().strftime("%Y%m%d")
    log_file = ESASS_DATA_DIR / "logs" / f"log_{today}.jsonl"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


if __name__ == "__main__":
    main()
