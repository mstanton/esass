#!/usr/bin/env python3
"""
ESASS PostToolUse Hook for Claude Code.

Captures tool calls from Claude Code and logs them to ESASS.
Run via: python -m esass.hooks.post_tool_use

Setup (automated via `esass init`):
    Add to ~/.claude/hooks.json:
    {
      "hooks": {
        "PostToolUse": [{
          "command": "python -m esass.hooks.post_tool_use",
          "timeout": 5000
        }]
      }
    }
"""

import json
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from esass.config import load_config, get_data_dir
except ImportError:
    # Fallback if esass not properly installed
    load_config = None

try:
    from esass.probes.config import ESASSProbeSystemConfig, create_default_probes
    from esass.probes.registry import ProbeRegistry
    from esass.probes.base import ProbeContext

    PROBES_AVAILABLE = True
except ImportError:
    PROBES_AVAILABLE = False


def _get_data_dir() -> Path:
    """Get data directory using config chain or env var fallback."""
    if load_config is not None:
        try:
            config = load_config()
            return get_data_dir(config)
        except Exception:
            pass
    return Path(
        os.environ.get("ESASS_DATA_DIR", str(Path.home() / ".esass" / "data"))
    )


ESASS_DATA_DIR = _get_data_dir()


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
        except Exception:
            pass

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

    if tool_name in ["Read", "Write", "Edit"]:
        context["category"] = "file_operation"
        context["target"] = params.get("file_path", "")
        context["action"] = tool_name.lower()

        if context["target"]:
            ext = Path(context["target"]).suffix.lower()
            if ext:
                context["tags"].append(f"filetype:{ext}")

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

        state["recent_tools"].append(
            {
                "tool": tool_name,
                "category": context["category"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        state["recent_tools"] = state["recent_tools"][-10:]

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
        pass


class CapturePipeline:
    """Simple pipeline to capture probe entries in-process."""

    def __init__(self):
        self.entries = []

    def submit(self, entries):
        self.entries.extend(entries)


def log_entry_object(entry):
    """Log a LogEntry object directly."""
    today = datetime.now().strftime("%Y%m%d")
    log_file = ESASS_DATA_DIR / "logs" / f"log_{today}.jsonl"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def main():
    """Process hook input from Claude Code."""
    ensure_data_dir()

    registry = None
    capture_pipeline = CapturePipeline()

    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            return

        hook_data = json.loads(input_data)

        debug_log = ESASS_DATA_DIR / "logs" / "hook_debug.log"
        with open(debug_log, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now().isoformat()}] Keys: {list(hook_data.keys())}\n"
            )

        tool_name = hook_data.get("tool_name", hook_data.get("name", "unknown"))
        tool_input = hook_data.get("tool_input", hook_data.get("input", {}))
        tool_output = hook_data.get("tool_result", hook_data.get("tool_output", ""))
        error = hook_data.get("error")
        success = error is None
        session_id = get_session_id()

        if not tool_name or tool_name == "unknown":
            return

        # Notify Probes if available
        if registry:
            event_data = {
                "tool_name": tool_name,
                "parameters": tool_input,
                "result": str(tool_output)[:1000],
                "success": success,
                "error": error,
            }
            ts = datetime.now()

            registry.notify(
                "tool_call_start",
                {
                    "tool_name": tool_name,
                    "parameters": tool_input,
                    "call_id": "hook-last",
                },
                {"session_id": session_id, "timestamp": ts},
            )

            registry.notify(
                "tool_call_complete" if success else "tool_call_error",
                event_data,
                {"session_id": session_id, "timestamp": ts},
            )

            if capture_pipeline.entries:
                for obs in capture_pipeline.entries:
                    log_entry_object(obs)

        # Standard Context Extraction
        context = extract_context(tool_name, tool_input)

        # Log the primary tool event
        log_data = {
            "tool_name": tool_name,
            "parameters": tool_input,
            "result_preview": str(tool_output)[:500] if tool_output else None,
            "context": context,
            "success": success,
            "error": error,
        }
        log_event("tool_call", log_data)

        # Update sequence tracking
        update_sequence_state(tool_name, context)

        # Debug log
        with open(debug_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] Captured {tool_name}\n")

    except Exception as e:
        try:
            debug_log = ESASS_DATA_DIR / "logs" / "hook_debug.log"
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] Error: {str(e)}\n")
            log_event("hook_error", {"error": str(e)})
        except Exception:
            pass


if __name__ == "__main__":
    main()
