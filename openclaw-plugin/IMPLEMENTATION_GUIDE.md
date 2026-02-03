# ESASS × OpenClaw Implementation Guide

## Complete Code Implementation for the Recursive Learning Loop

**Version**: 1.0.0  
**Prerequisites**: Python 3.8+, Node.js 22+, OpenClaw installed

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Core Bridge Implementation](#core-bridge-implementation)
3. [OpenClaw Event Hooks](#openclaw-event-hooks)
4. [ESASS Skill Adapter](#esass-skill-adapter)
5. [ClawHub Publisher](#clawhub-publisher)
6. [Recursive Loop Controller](#recursive-loop-controller)
7. [Configuration](#configuration)
8. [Testing](#testing)

---

## Project Structure

```
esass-openclaw-bridge/
├── src/
│   ├── __init__.py
│   ├── bridge/
│   │   ├── __init__.py
│   │   ├── openclaw_hooks.py       # Event capture from OpenClaw
│   │   ├── event_translator.py     # Translate to ESASS format
│   │   └── feedback_collector.py   # Skill usage feedback
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── skill_formatter.py      # ESASS → SKILL.md conversion
│   │   ├── clawhub_client.py       # ClawHub API client
│   │   └── openclaw_loader.py      # Skill installation
│   │
│   ├── loop/
│   │   ├── __init__.py
│   │   ├── controller.py           # Main loop orchestration
│   │   ├── scheduler.py            # Timing and triggers
│   │   └── metrics.py              # Loop health monitoring
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py             # Configuration management
│
├── skills/
│   └── generated/                  # ESASS-generated skills
│
├── tests/
│   ├── test_bridge.py
│   ├── test_adapters.py
│   └── test_loop.py
│
├── pyproject.toml
└── README.md
```

---

## Core Bridge Implementation

### `src/bridge/openclaw_hooks.py`

```python
"""
OpenClaw Event Hooks for ESASS Integration

Captures events from OpenClaw's agent loop and forwards them to ESASS probes.
"""

import json
import asyncio
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import os

# ESASS imports
from esass.probes.config import initialize_system
from esass.probes.registry import GlobalRegistry


class OpenClawEventType(Enum):
    """Event types emitted by OpenClaw agent loop"""
    # Agent lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    
    # Message flow
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    
    # Agent reasoning
    THINKING_START = "thinking_start"
    THINKING_BLOCK = "thinking_block"
    THINKING_END = "thinking_end"
    
    # Tool execution
    TOOL_SELECTED = "tool_selected"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"
    
    # Skill usage
    SKILL_ACTIVATED = "skill_activated"
    SKILL_COMPLETED = "skill_completed"
    SKILL_FAILED = "skill_failed"
    
    # Decision points
    APPROACH_SELECTED = "approach_selected"
    PLAN_MODE_ENTERED = "plan_mode_entered"


@dataclass
class OpenClawEvent:
    """Structured event from OpenClaw"""
    event_type: OpenClawEventType
    timestamp: datetime
    session_id: str
    data: dict = field(default_factory=dict)
    channel: Optional[str] = None  # whatsapp, telegram, etc.
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For event causality


class OpenClawESASSBridge:
    """
    Bridges OpenClaw events to ESASS observation system.
    
    This is the primary integration point that hooks into OpenClaw's
    agent loop and translates events for ESASS pattern detection.
    """
    
    def __init__(
        self,
        data_dir: str = "./data/esass",
        enable_feedback: bool = True,
        sample_rate: float = 1.0
    ):
        self.data_dir = data_dir
        self.enable_feedback = enable_feedback
        self.sample_rate = sample_rate
        
        # Initialize ESASS system
        self.registry, self.pipeline, self.config = initialize_system(
            data_dir=data_dir,
            sample_rate=sample_rate
        )
        
        # Track active sessions
        self._sessions: dict[str, dict] = {}
        self._pending_tools: dict[str, dict] = {}
        
        # Skill usage tracking for feedback loop
        self._skill_activations: dict[str, list] = {}
        
    async def on_event(self, event: OpenClawEvent) -> None:
        """
        Main event handler - routes OpenClaw events to appropriate ESASS probes.
        """
        handlers = {
            OpenClawEventType.SESSION_START: self._handle_session_start,
            OpenClawEventType.SESSION_END: self._handle_session_end,
            OpenClawEventType.THINKING_BLOCK: self._handle_thinking,
            OpenClawEventType.TOOL_CALL_START: self._handle_tool_start,
            OpenClawEventType.TOOL_CALL_COMPLETE: self._handle_tool_complete,
            OpenClawEventType.TOOL_CALL_ERROR: self._handle_tool_error,
            OpenClawEventType.SKILL_ACTIVATED: self._handle_skill_activated,
            OpenClawEventType.SKILL_COMPLETED: self._handle_skill_completed,
            OpenClawEventType.APPROACH_SELECTED: self._handle_decision,
        }
        
        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
    
    async def _handle_session_start(self, event: OpenClawEvent) -> None:
        """Track new session"""
        self._sessions[event.session_id] = {
            "start_time": event.timestamp,
            "channel": event.channel,
            "user_id": event.user_id,
            "agent_id": event.agent_id,
            "events": []
        }
    
    async def _handle_session_end(self, event: OpenClawEvent) -> None:
        """Finalize session and flush events"""
        if event.session_id in self._sessions:
            session = self._sessions.pop(event.session_id)
            # Session data is already logged via probes
    
    async def _handle_thinking(self, event: OpenClawEvent) -> None:
        """Forward thinking blocks to ReasoningProbe"""
        from esass.probes.base import ProbeContext
        
        context = ProbeContext(
            session_id=event.session_id,
            timestamp=event.timestamp,
            metadata={
                "channel": event.channel,
                "user_id": event.user_id,
                "correlation_id": event.correlation_id
            }
        )
        
        self.registry.notify(
            event_type="thinking_block",
            data={
                "content": event.data.get("content", ""),
                "thinking_type": event.data.get("type", "general")
            },
            context=context
        )
    
    async def _handle_tool_start(self, event: OpenClawEvent) -> None:
        """Forward tool execution start to ToolCallProbe"""
        from esass.probes.base import ProbeContext
        
        tool_name = event.data.get("tool_name", "unknown")
        parameters = event.data.get("parameters", {})
        call_id = event.data.get("call_id", str(event.timestamp.timestamp()))
        
        context = ProbeContext(
            session_id=event.session_id,
            timestamp=event.timestamp,
            metadata={
                "channel": event.channel,
                "correlation_id": event.correlation_id
            }
        )
        
        # Store for completion matching
        self._pending_tools[call_id] = {
            "tool_name": tool_name,
            "start_time": event.timestamp,
            "context": context
        }
        
        self.registry.notify(
            event_type="tool_call_start",
            data={
                "call_id": call_id,
                "tool_name": tool_name,
                "parameters": parameters
            },
            context=context
        )
    
    async def _handle_tool_complete(self, event: OpenClawEvent) -> None:
        """Forward tool completion to ToolCallProbe"""
        call_id = event.data.get("call_id")
        
        if call_id and call_id in self._pending_tools:
            pending = self._pending_tools.pop(call_id)
            
            self.registry.notify(
                event_type="tool_call_complete",
                data={
                    "call_id": call_id,
                    "tool_name": pending["tool_name"],
                    "result": event.data.get("result"),
                    "success": event.data.get("success", True),
                    "duration_ms": (
                        event.timestamp - pending["start_time"]
                    ).total_seconds() * 1000
                },
                context=pending["context"]
            )
    
    async def _handle_tool_error(self, event: OpenClawEvent) -> None:
        """Forward tool errors to ToolCallProbe"""
        call_id = event.data.get("call_id")
        
        if call_id and call_id in self._pending_tools:
            pending = self._pending_tools.pop(call_id)
            
            self.registry.notify(
                event_type="tool_call_error",
                data={
                    "call_id": call_id,
                    "tool_name": pending["tool_name"],
                    "error_type": event.data.get("error_type", "unknown"),
                    "error_message": event.data.get("error_message", "")
                },
                context=pending["context"]
            )
    
    async def _handle_skill_activated(self, event: OpenClawEvent) -> None:
        """Track skill activation for feedback loop"""
        skill_name = event.data.get("skill_name")
        
        if skill_name:
            if skill_name not in self._skill_activations:
                self._skill_activations[skill_name] = []
            
            self._skill_activations[skill_name].append({
                "session_id": event.session_id,
                "timestamp": event.timestamp,
                "trigger": event.data.get("trigger"),
                "context": event.data.get("context")
            })
            
            # Emit as decision event
            from esass.probes.base import ProbeContext
            context = ProbeContext(
                session_id=event.session_id,
                timestamp=event.timestamp
            )
            
            self.registry.notify(
                event_type="tool_selected",
                data={
                    "decision": f"skill:{skill_name}",
                    "trigger": event.data.get("trigger"),
                    "is_skill": True
                },
                context=context
            )
    
    async def _handle_skill_completed(self, event: OpenClawEvent) -> None:
        """Track skill completion for feedback"""
        skill_name = event.data.get("skill_name")
        success = event.data.get("success", True)
        
        # Update activation record with outcome
        if skill_name in self._skill_activations:
            activations = self._skill_activations[skill_name]
            for activation in reversed(activations):
                if activation["session_id"] == event.session_id:
                    activation["outcome"] = "success" if success else "failure"
                    activation["completed_at"] = event.timestamp
                    break
    
    async def _handle_decision(self, event: OpenClawEvent) -> None:
        """Forward decision points to DecisionProbe"""
        from esass.probes.base import ProbeContext
        
        context = ProbeContext(
            session_id=event.session_id,
            timestamp=event.timestamp
        )
        
        self.registry.notify(
            event_type="tool_selected",
            data={
                "decision": event.data.get("approach"),
                "options": event.data.get("alternatives", []),
                "rationale": event.data.get("rationale", "")
            },
            context=context
        )
    
    def get_skill_feedback(self, skill_name: str) -> dict:
        """Get feedback metrics for a skill"""
        if skill_name not in self._skill_activations:
            return {"activations": 0, "success_rate": 0.0}
        
        activations = self._skill_activations[skill_name]
        completed = [a for a in activations if "outcome" in a]
        successes = [a for a in completed if a["outcome"] == "success"]
        
        return {
            "activations": len(activations),
            "completions": len(completed),
            "successes": len(successes),
            "success_rate": len(successes) / len(completed) if completed else 0.0
        }
    
    def flush(self) -> None:
        """Flush all pending events"""
        self.registry.flush()
        self.pipeline.flush()
    
    def shutdown(self) -> None:
        """Graceful shutdown"""
        self.flush()
        self.pipeline.shutdown()


# Singleton bridge instance
_bridge_instance: Optional[OpenClawESASSBridge] = None


def get_bridge() -> OpenClawESASSBridge:
    """Get or create the bridge singleton"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OpenClawESASSBridge(
            data_dir=os.environ.get("ESASS_DATA_DIR", "./data/esass"),
            sample_rate=float(os.environ.get("ESASS_SAMPLE_RATE", "1.0"))
        )
    return _bridge_instance


# Convenience functions for OpenClaw integration
async def emit_event(event_type: str, session_id: str, data: dict, **kwargs) -> None:
    """Emit an event to ESASS from OpenClaw"""
    bridge = get_bridge()
    event = OpenClawEvent(
        event_type=OpenClawEventType(event_type),
        timestamp=datetime.utcnow(),
        session_id=session_id,
        data=data,
        **kwargs
    )
    await bridge.on_event(event)
```

---

## ESASS Skill Adapter

### `src/adapters/skill_formatter.py`

```python
"""
ESASS Skill to OpenClaw SKILL.md Converter

Transforms ESASS SkillManifest objects into OpenClaw-compatible SKILL.md files.
"""

import yaml
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Assuming ESASS models
from esass_prototype.models import SkillManifest, PatternDefinition


@dataclass
class OpenClawSkillMetadata:
    """OpenClaw SKILL.md frontmatter structure"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "esass-genesis"
    genesis_type: str = "emergent"
    pattern_id: Optional[str] = None
    confidence: float = 0.0
    support: int = 0
    first_observed: Optional[str] = None
    triggers: list = None
    capabilities: list = None
    parent_skills: list = None
    child_skills: list = None
    generation: int = 1
    
    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
        if self.capabilities is None:
            self.capabilities = []
        if self.parent_skills is None:
            self.parent_skills = []
        if self.child_skills is None:
            self.child_skills = []


class SkillFormatter:
    """
    Converts ESASS skills to OpenClaw SKILL.md format.
    
    This adapter ensures generated skills are compatible with OpenClaw's
    skill loading system and can be published to ClawHub.
    """
    
    def __init__(self, output_dir: str = "./skills/generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def format_skill(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition] = None
    ) -> str:
        """
        Convert ESASS SkillManifest to SKILL.md content.
        
        Args:
            manifest: ESASS skill manifest
            pattern: Optional source pattern for additional context
            
        Returns:
            Complete SKILL.md file content
        """
        metadata = self._build_metadata(manifest, pattern)
        frontmatter = self._format_frontmatter(metadata)
        body = self._generate_body(manifest, pattern, metadata)
        
        return f"{frontmatter}\n{body}"
    
    def _build_metadata(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition]
    ) -> OpenClawSkillMetadata:
        """Extract metadata for frontmatter"""
        
        # Parse triggers from manifest
        triggers = []
        for trigger in manifest.triggers:
            if trigger.startswith("intent_match:"):
                # Convert "intent_match:git,commit" to "git commit"
                intent = trigger.replace("intent_match:", "").replace(",", " ")
                triggers.append(intent)
        
        return OpenClawSkillMetadata(
            name=self._format_skill_name(manifest.name),
            description=manifest.description,
            version=manifest.version,
            author="esass-genesis",
            genesis_type=manifest.genesis_type,
            pattern_id=manifest.source_pattern_ids[0] if manifest.source_pattern_ids else None,
            confidence=pattern.confidence if pattern else 0.9,
            support=pattern.support if pattern else 0,
            first_observed=pattern.first_seen if pattern else datetime.utcnow().isoformat(),
            triggers=triggers or self._infer_triggers(manifest),
            capabilities=list(manifest.capabilities),
            parent_skills=getattr(manifest, 'parent_skills', []),
            child_skills=getattr(manifest, 'child_skills', []),
            generation=getattr(manifest, 'generation', 1)
        )
    
    def _format_skill_name(self, name: str) -> str:
        """Convert skill name to kebab-case for OpenClaw"""
        return name.replace("_", "-").lower()
    
    def _infer_triggers(self, manifest: SkillManifest) -> list:
        """Infer natural language triggers from skill"""
        triggers = []
        
        # Extract from capabilities
        capability_triggers = {
            "git_operations": ["git", "commit", "push", "pull"],
            "file_operations": ["read file", "write file", "edit"],
            "code_analysis": ["analyze code", "review", "check"],
            "testing": ["run tests", "test", "coverage"],
            "documentation": ["document", "docs", "readme"]
        }
        
        for cap in manifest.capabilities:
            if cap in capability_triggers:
                triggers.extend(capability_triggers[cap])
        
        return triggers[:5]  # Limit to 5 triggers
    
    def _format_frontmatter(self, metadata: OpenClawSkillMetadata) -> str:
        """Generate YAML frontmatter"""
        data = {
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "author": metadata.author,
            "genesis": {
                "type": metadata.genesis_type,
                "pattern_id": metadata.pattern_id,
                "confidence": round(metadata.confidence, 2),
                "support": metadata.support,
                "first_observed": metadata.first_observed
            },
            "metadata": {
                "openclaw": {
                    "triggers": metadata.triggers,
                    "capabilities": metadata.capabilities,
                    "evolution": {
                        "parent_skills": metadata.parent_skills,
                        "child_skills": metadata.child_skills,
                        "generation": metadata.generation
                    }
                }
            }
        }
        
        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_content}---"
    
    def _generate_body(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition],
        metadata: OpenClawSkillMetadata
    ) -> str:
        """Generate the markdown body of the skill"""
        
        title = self._title_case(metadata.name.replace("-", " "))
        
        sections = [
            f"# {title}",
            "",
            "## Overview",
            manifest.description,
            "",
            "## When to Use",
            self._generate_when_to_use(metadata),
            "",
            "## Workflow",
            self._generate_workflow(manifest, pattern),
            "",
            "## Error Handling",
            self._generate_error_handling(manifest),
            "",
            "## Examples",
            self._generate_examples(manifest, metadata),
            "",
            "## Dependencies",
            self._generate_dependencies(manifest),
            "",
            "## Evolution History",
            self._generate_evolution_history(manifest, metadata)
        ]
        
        return "\n".join(sections)
    
    def _title_case(self, text: str) -> str:
        """Convert text to title case"""
        return " ".join(word.capitalize() for word in text.split())
    
    def _generate_when_to_use(self, metadata: OpenClawSkillMetadata) -> str:
        """Generate when-to-use section"""
        triggers_text = ", ".join(f'"{t}"' for t in metadata.triggers[:3])
        return f"""Use this skill when the user wants to {metadata.description.lower()}. 
This skill is triggered by phrases like {triggers_text}."""
    
    def _generate_workflow(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition]
    ) -> str:
        """Generate workflow section from pattern sequence"""
        if pattern and pattern.sequence:
            steps = []
            for i, step in enumerate(pattern.sequence, 1):
                # Parse step like "tool_usage:git,status"
                parts = step.split(":")
                event_type = parts[0]
                details = parts[1] if len(parts) > 1 else ""
                
                step_text = self._format_workflow_step(event_type, details)
                steps.append(f"{i}. **{step_text['title']}**\n   {step_text['description']}")
            
            return "\n\n".join(steps)
        
        return manifest.implementation_summary or "See implementation details."
    
    def _format_workflow_step(self, event_type: str, details: str) -> dict:
        """Format a single workflow step"""
        templates = {
            "reasoning": {
                "title": "Analyze Context",
                "description": f"Evaluate the situation: {details.replace(',', ', ')}"
            },
            "tool_usage": {
                "title": f"Execute {details.split(',')[0].title() if details else 'Tool'}",
                "description": f"```bash\n{details.replace(',', ' ')}\n```"
            },
            "decision": {
                "title": "Make Decision",
                "description": f"Choose approach based on: {details.replace(',', ', ')}"
            },
            "outcome": {
                "title": "Verify Result",
                "description": "Confirm successful execution and report to user"
            }
        }
        
        return templates.get(event_type, {
            "title": event_type.replace("_", " ").title(),
            "description": details
        })
    
    def _generate_error_handling(self, manifest: SkillManifest) -> str:
        """Generate error handling section"""
        # Infer from capabilities
        handlers = []
        
        if "git_operations" in manifest.capabilities:
            handlers.extend([
                "- **No staged changes**: Prompt user to stage or offer `git add -A`",
                "- **Merge conflicts**: Detect and guide resolution",
                "- **Detached HEAD**: Warn and suggest branch creation"
            ])
        
        if "file_operations" in manifest.capabilities:
            handlers.extend([
                "- **File not found**: Search for alternatives or prompt for path",
                "- **Permission denied**: Suggest chmod or elevated permissions",
                "- **Encoding issues**: Detect and handle non-UTF8 files"
            ])
        
        if "code_analysis" in manifest.capabilities:
            handlers.extend([
                "- **Syntax errors**: Report location and suggest fixes",
                "- **Large files**: Warn about performance and offer chunking"
            ])
        
        return "\n".join(handlers) if handlers else "- Handle errors gracefully and report to user"
    
    def _generate_examples(
        self,
        manifest: SkillManifest,
        metadata: OpenClawSkillMetadata
    ) -> str:
        """Generate example usage"""
        examples = []
        
        for i, trigger in enumerate(metadata.triggers[:2], 1):
            examples.append(f"""### Example {i}
User: "{trigger.title()}"
Action: {manifest.description}""")
        
        return "\n\n".join(examples) if examples else "See workflow for usage examples."
    
    def _generate_dependencies(self, manifest: SkillManifest) -> str:
        """Generate dependencies section"""
        deps = []
        
        capability_deps = {
            "git_operations": "- git (required)",
            "file_operations": "- filesystem access (required)",
            "web_operations": "- curl or web tool (required)",
            "code_analysis": "- language-specific linters (optional)",
            "testing": "- test framework (project-dependent)"
        }
        
        for cap in manifest.capabilities:
            if cap in capability_deps:
                deps.append(capability_deps[cap])
        
        return "\n".join(deps) if deps else "- None"
    
    def _generate_evolution_history(
        self,
        manifest: SkillManifest,
        metadata: OpenClawSkillMetadata
    ) -> str:
        """Generate evolution history"""
        history = [
            f"- v{metadata.version}: Initial emergent pattern detection (ESASS genesis)"
        ]
        
        if metadata.parent_skills:
            history.append(f"- Derived from: {', '.join(metadata.parent_skills)}")
        
        return "\n".join(history)
    
    def save_skill(
        self,
        manifest: SkillManifest,
        pattern: Optional[PatternDefinition] = None
    ) -> Path:
        """Save skill to file system"""
        content = self.format_skill(manifest, pattern)
        skill_name = self._format_skill_name(manifest.name)
        
        # Create skill directory
        skill_dir = self.output_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Write SKILL.md
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content)
        
        return skill_file
    
    def batch_convert(
        self,
        manifests: list[SkillManifest],
        patterns: Optional[dict[str, PatternDefinition]] = None
    ) -> list[Path]:
        """Convert multiple skills"""
        patterns = patterns or {}
        saved = []
        
        for manifest in manifests:
            pattern = None
            if manifest.source_pattern_ids:
                pattern = patterns.get(manifest.source_pattern_ids[0])
            
            path = self.save_skill(manifest, pattern)
            saved.append(path)
        
        return saved
```

---

## ClawHub Publisher

### `src/adapters/clawhub_client.py`

```python
"""
ClawHub Publishing Client

Automates skill publication to ClawHub registry with versioning and metadata.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class PublishResult(Enum):
    SUCCESS = "success"
    ALREADY_EXISTS = "already_exists"
    VALIDATION_FAILED = "validation_failed"
    AUTH_FAILED = "auth_failed"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class PublishResponse:
    result: PublishResult
    skill_slug: str
    version: str
    url: Optional[str] = None
    message: Optional[str] = None


class ClawHubClient:
    """
    Client for interacting with ClawHub skill registry.
    
    Supports publish, search, and sync operations for ESASS-generated skills.
    """
    
    def __init__(
        self,
        registry_url: str = "https://clawhub.com",
        token: Optional[str] = None,
        auto_bump: str = "patch"  # patch, minor, major
    ):
        self.registry_url = registry_url
        self.token = token or os.environ.get("CLAWHUB_TOKEN")
        self.auto_bump = auto_bump
        
        # Verify clawhub CLI is installed
        self._verify_cli()
    
    def _verify_cli(self) -> None:
        """Check if clawhub CLI is available"""
        try:
            subprocess.run(
                ["clawhub", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "clawhub CLI not found. Install with: npm i -g clawhub"
            )
    
    def _run_clawhub(self, args: list, capture: bool = True) -> subprocess.CompletedProcess:
        """Run clawhub CLI command"""
        cmd = ["clawhub"] + args
        
        if self.token:
            cmd.extend(["--token", self.token])
        
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True
        )
    
    def authenticate(self, token: Optional[str] = None) -> bool:
        """Authenticate with ClawHub"""
        token = token or self.token
        if not token:
            # Browser-based login
            result = self._run_clawhub(["login"])
            return result.returncode == 0
        
        # Token-based login
        result = self._run_clawhub(["login", "--token", token])
        return result.returncode == 0
    
    def whoami(self) -> Optional[str]:
        """Get current authenticated user"""
        result = self._run_clawhub(["whoami"])
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for skills on ClawHub"""
        result = self._run_clawhub([
            "search", query,
            "--limit", str(limit),
            "--json"  # If supported
        ])
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Parse text output
                return self._parse_search_output(result.stdout)
        
        return []
    
    def _parse_search_output(self, output: str) -> list[dict]:
        """Parse search output if not JSON"""
        skills = []
        for line in output.strip().split("\n"):
            if line.strip():
                # Basic parsing - adjust based on actual output format
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    skills.append({
                        "slug": parts[0].strip(),
                        "description": parts[1].strip()
                    })
        return skills
    
    def skill_exists(self, slug: str) -> bool:
        """Check if skill exists on ClawHub"""
        results = self.search(slug, limit=1)
        return any(r.get("slug") == slug for r in results)
    
    def publish(
        self,
        skill_path: Path,
        slug: Optional[str] = None,
        name: Optional[str] = None,
        version: Optional[str] = None,
        changelog: str = "ESASS auto-generated skill",
        tags: list[str] = None
    ) -> PublishResponse:
        """
        Publish a skill to ClawHub.
        
        Args:
            skill_path: Path to skill directory containing SKILL.md
            slug: Skill slug (derived from directory name if not provided)
            name: Display name
            version: Semver version
            changelog: Version changelog
            tags: Tags for the skill (default: ["latest", "esass-generated"])
            
        Returns:
            PublishResponse with result status
        """
        skill_path = Path(skill_path)
        
        if not (skill_path / "SKILL.md").exists():
            return PublishResponse(
                result=PublishResult.VALIDATION_FAILED,
                skill_slug=slug or skill_path.name,
                version=version or "0.0.0",
                message="SKILL.md not found"
            )
        
        # Determine slug from path if not provided
        slug = slug or skill_path.name
        
        # Read SKILL.md for metadata
        metadata = self._read_skill_metadata(skill_path / "SKILL.md")
        name = name or metadata.get("name", slug)
        version = version or metadata.get("version", "1.0.0")
        
        # Default tags
        tags = tags or ["latest", "esass-generated"]
        
        # Build command
        args = [
            "publish", str(skill_path),
            "--slug", slug,
            "--name", name,
            "--version", version,
            "--changelog", changelog,
            "--tags", ",".join(tags)
        ]
        
        result = self._run_clawhub(args)
        
        if result.returncode == 0:
            return PublishResponse(
                result=PublishResult.SUCCESS,
                skill_slug=slug,
                version=version,
                url=f"{self.registry_url}/skills/{slug}",
                message="Successfully published"
            )
        
        # Parse error
        error_msg = result.stderr or result.stdout
        
        if "already exists" in error_msg.lower():
            return PublishResponse(
                result=PublishResult.ALREADY_EXISTS,
                skill_slug=slug,
                version=version,
                message="Version already exists"
            )
        
        if "unauthorized" in error_msg.lower() or "auth" in error_msg.lower():
            return PublishResponse(
                result=PublishResult.AUTH_FAILED,
                skill_slug=slug,
                version=version,
                message="Authentication failed"
            )
        
        return PublishResponse(
            result=PublishResult.UNKNOWN_ERROR,
            skill_slug=slug,
            version=version,
            message=error_msg
        )
    
    def _read_skill_metadata(self, skill_file: Path) -> dict:
        """Read metadata from SKILL.md frontmatter"""
        import yaml
        
        content = skill_file.read_text()
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1])
                except yaml.YAMLError:
                    pass
        
        return {}
    
    def install(self, slug: str, version: Optional[str] = None) -> bool:
        """Install a skill from ClawHub"""
        args = ["install", slug]
        if version:
            args.extend(["--version", version])
        
        result = self._run_clawhub(args)
        return result.returncode == 0
    
    def update(self, slug: Optional[str] = None, all_skills: bool = False) -> bool:
        """Update installed skills"""
        if all_skills:
            args = ["update", "--all"]
        else:
            args = ["update", slug]
        
        result = self._run_clawhub(args)
        return result.returncode == 0
    
    def sync(
        self,
        skill_dirs: list[Path],
        dry_run: bool = False,
        bump: Optional[str] = None
    ) -> list[PublishResponse]:
        """
        Sync multiple skill directories to ClawHub.
        
        Args:
            skill_dirs: List of skill directories to sync
            dry_run: Preview without publishing
            bump: Version bump type (patch, minor, major)
            
        Returns:
            List of publish responses
        """
        responses = []
        bump = bump or self.auto_bump
        
        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                continue
            
            if not (skill_dir / "SKILL.md").exists():
                continue
            
            if dry_run:
                print(f"Would publish: {skill_dir.name}")
                continue
            
            # Check if update needed
            slug = skill_dir.name
            metadata = self._read_skill_metadata(skill_dir / "SKILL.md")
            current_version = metadata.get("version", "1.0.0")
            
            if self.skill_exists(slug):
                # Bump version for update
                new_version = self._bump_version(current_version, bump)
                response = self.publish(
                    skill_dir,
                    version=new_version,
                    changelog=f"ESASS auto-update ({bump})"
                )
            else:
                # New skill
                response = self.publish(skill_dir)
            
            responses.append(response)
        
        return responses
    
    def _bump_version(self, version: str, bump: str) -> str:
        """Bump semver version"""
        parts = version.split(".")
        if len(parts) != 3:
            return "1.0.0"
        
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if bump == "major":
            return f"{major + 1}.0.0"
        elif bump == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"


class ESASSClawHubPublisher:
    """
    High-level publisher for ESASS-generated skills.
    
    Handles the full workflow from skill manifest to published skill.
    """
    
    def __init__(
        self,
        formatter: "SkillFormatter",
        client: ClawHubClient,
        require_confidence: float = 0.85,
        require_support: int = 15
    ):
        self.formatter = formatter
        self.client = client
        self.require_confidence = require_confidence
        self.require_support = require_support
    
    def publish_skill(
        self,
        manifest: "SkillManifest",
        pattern: Optional["PatternDefinition"] = None,
        auto_authenticate: bool = True
    ) -> PublishResponse:
        """
        Publish an ESASS skill manifest to ClawHub.
        
        Args:
            manifest: ESASS skill manifest
            pattern: Source pattern (for metadata)
            auto_authenticate: Attempt auth if needed
            
        Returns:
            PublishResponse
        """
        # Validate quality thresholds
        if pattern:
            if pattern.confidence < self.require_confidence:
                return PublishResponse(
                    result=PublishResult.VALIDATION_FAILED,
                    skill_slug=manifest.name,
                    version=manifest.version,
                    message=f"Confidence {pattern.confidence} below threshold {self.require_confidence}"
                )
            
            if pattern.support < self.require_support:
                return PublishResponse(
                    result=PublishResult.VALIDATION_FAILED,
                    skill_slug=manifest.name,
                    version=manifest.version,
                    message=f"Support {pattern.support} below threshold {self.require_support}"
                )
        
        # Convert to SKILL.md
        skill_path = self.formatter.save_skill(manifest, pattern)
        
        # Authenticate if needed
        if auto_authenticate and not self.client.whoami():
            self.client.authenticate()
        
        # Publish
        return self.client.publish(skill_path.parent)
    
    def publish_batch(
        self,
        manifests: list["SkillManifest"],
        patterns: Optional[dict[str, "PatternDefinition"]] = None
    ) -> list[PublishResponse]:
        """Publish multiple skills"""
        patterns = patterns or {}
        responses = []
        
        for manifest in manifests:
            pattern = None
            if manifest.source_pattern_ids:
                pattern = patterns.get(manifest.source_pattern_ids[0])
            
            response = self.publish_skill(manifest, pattern)
            responses.append(response)
        
        return responses
```

---

## Recursive Loop Controller

### `src/loop/controller.py`

```python
"""
Recursive Learning Loop Controller

Orchestrates the complete ESASS → OpenClaw → ClawHub → OpenClaw cycle.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

# Internal imports
from ..bridge.openclaw_hooks import OpenClawESASSBridge, get_bridge
from ..adapters.skill_formatter import SkillFormatter
from ..adapters.clawhub_client import ClawHubClient, ESASSClawHubPublisher, PublishResult

# ESASS imports
from esass_prototype.storage.log_store import LogStore
from esass_prototype.storage.pattern_store import PatternStore
from esass_prototype.storage.skill_store import SkillStore
from esass_prototype.analysis.pattern_detector import TemporalPatternDetector
from esass_prototype.genesis.template import SkillTemplateGenerator


logger = logging.getLogger(__name__)


class LoopPhase(Enum):
    """Current phase of the recursive loop"""
    IDLE = "idle"
    OBSERVING = "observing"
    DETECTING = "detecting"
    GENERATING = "generating"
    PUBLISHING = "publishing"
    SYNCING = "syncing"


@dataclass
class LoopMetrics:
    """Metrics for loop health monitoring"""
    cycles_completed: int = 0
    events_observed: int = 0
    patterns_detected: int = 0
    skills_generated: int = 0
    skills_published: int = 0
    publish_failures: int = 0
    last_cycle_start: Optional[datetime] = None
    last_cycle_end: Optional[datetime] = None
    last_cycle_duration_seconds: float = 0.0
    
    # Rolling averages
    avg_patterns_per_cycle: float = 0.0
    avg_skills_per_cycle: float = 0.0


@dataclass
class LoopConfig:
    """Configuration for the recursive loop"""
    # Timing
    observation_window_hours: int = 24
    cycle_interval_hours: int = 6
    min_events_for_detection: int = 100
    
    # Pattern detection
    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7
    
    # Skill generation
    auto_generate: bool = True
    max_skills_per_cycle: int = 5
    
    # Publishing
    auto_publish: bool = True
    publish_confidence_threshold: float = 0.85
    publish_support_threshold: int = 15
    
    # Safety
    require_human_approval: bool = False
    rate_limit_skills_per_day: int = 10


class RecursiveLoopController:
    """
    Main controller for the ESASS × OpenClaw × ClawHub recursive learning loop.
    
    This controller orchestrates:
    1. Event observation from OpenClaw via ESASS bridge
    2. Pattern detection from accumulated logs
    3. Skill generation from validated patterns
    4. Automatic publishing to ClawHub
    5. Skill sync back to OpenClaw workspaces
    """
    
    def __init__(
        self,
        config: Optional[LoopConfig] = None,
        bridge: Optional[OpenClawESASSBridge] = None,
        formatter: Optional[SkillFormatter] = None,
        clawhub_client: Optional[ClawHubClient] = None
    ):
        self.config = config or LoopConfig()
        self.bridge = bridge or get_bridge()
        self.formatter = formatter or SkillFormatter()
        self.clawhub = clawhub_client or ClawHubClient()
        
        # Stores
        self.log_store = LogStore()
        self.pattern_store = PatternStore()
        self.skill_store = SkillStore()
        
        # State
        self.phase = LoopPhase.IDLE
        self.metrics = LoopMetrics()
        self._running = False
        self._skills_published_today = 0
        self._last_publish_date: Optional[datetime] = None
        
        # Callbacks
        self._on_skill_generated: Optional[Callable] = None
        self._on_skill_published: Optional[Callable] = None
        self._on_cycle_complete: Optional[Callable] = None
    
    def on_skill_generated(self, callback: Callable) -> None:
        """Register callback for skill generation events"""
        self._on_skill_generated = callback
    
    def on_skill_published(self, callback: Callable) -> None:
        """Register callback for skill publish events"""
        self._on_skill_published = callback
    
    def on_cycle_complete(self, callback: Callable) -> None:
        """Register callback for cycle completion"""
        self._on_cycle_complete = callback
    
    async def start(self) -> None:
        """Start the recursive loop"""
        self._running = True
        logger.info("Starting recursive learning loop")
        
        while self._running:
            try:
                await self.run_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.config.cycle_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(60)  # Brief pause on error
    
    async def stop(self) -> None:
        """Stop the recursive loop"""
        self._running = False
        self.bridge.shutdown()
        logger.info("Stopped recursive learning loop")
    
    async def run_cycle(self) -> dict:
        """
        Execute one complete learning cycle.
        
        Returns:
            Cycle results summary
        """
        self.metrics.last_cycle_start = datetime.utcnow()
        logger.info(f"Starting learning cycle {self.metrics.cycles_completed + 1}")
        
        results = {
            "events_processed": 0,
            "patterns_detected": 0,
            "skills_generated": 0,
            "skills_published": 0,
            "errors": []
        }
        
        try:
            # Phase 1: Flush observation buffer
            self.phase = LoopPhase.OBSERVING
            self.bridge.flush()
            
            # Phase 2: Load and analyze logs
            self.phase = LoopPhase.DETECTING
            logs = self.log_store.read_last_n_days(
                self.config.observation_window_hours // 24 or 1
            )
            results["events_processed"] = len(logs)
            
            if len(logs) < self.config.min_events_for_detection:
                logger.info(
                    f"Insufficient events ({len(logs)}) for detection, "
                    f"need {self.config.min_events_for_detection}"
                )
                return results
            
            # Detect patterns
            detector = TemporalPatternDetector(
                min_support=self.config.min_support,
                min_confidence=self.config.min_confidence,
                min_stability_days=self.config.min_stability_days
            )
            patterns = detector.detect_patterns(logs)
            results["patterns_detected"] = len(patterns)
            
            # Filter to skill candidates
            candidates = [p for p in patterns if p.skill_candidate]
            logger.info(f"Detected {len(patterns)} patterns, {len(candidates)} candidates")
            
            # Save patterns
            for pattern in patterns:
                self.pattern_store.save(pattern)
            
            # Phase 3: Generate skills
            if self.config.auto_generate and candidates:
                self.phase = LoopPhase.GENERATING
                
                generator = SkillTemplateGenerator()
                skills = generator.generate_from_patterns(
                    candidates[:self.config.max_skills_per_cycle]
                )
                results["skills_generated"] = len(skills)
                
                # Save skills
                for skill in skills:
                    self.skill_store.save(skill)
                    
                    if self._on_skill_generated:
                        self._on_skill_generated(skill)
                
                # Phase 4: Publish to ClawHub
                if self.config.auto_publish:
                    self.phase = LoopPhase.PUBLISHING
                    published = await self._publish_skills(skills, candidates)
                    results["skills_published"] = published
            
            # Phase 5: Sync to OpenClaw
            self.phase = LoopPhase.SYNCING
            await self._sync_to_openclaw()
            
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            results["errors"].append(str(e))
        
        finally:
            self.phase = LoopPhase.IDLE
            self.metrics.last_cycle_end = datetime.utcnow()
            self.metrics.last_cycle_duration_seconds = (
                self.metrics.last_cycle_end - self.metrics.last_cycle_start
            ).total_seconds()
            self.metrics.cycles_completed += 1
            
            # Update rolling metrics
            self._update_rolling_metrics(results)
            
            if self._on_cycle_complete:
                self._on_cycle_complete(results)
        
        return results
    
    async def _publish_skills(
        self,
        skills: list,
        patterns: list
    ) -> int:
        """Publish generated skills to ClawHub"""
        # Check rate limit
        today = datetime.utcnow().date()
        if self._last_publish_date != today:
            self._skills_published_today = 0
            self._last_publish_date = today
        
        if self._skills_published_today >= self.config.rate_limit_skills_per_day:
            logger.warning("Daily skill publish limit reached")
            return 0
        
        # Create pattern lookup
        pattern_map = {p.pattern_id: p for p in patterns}
        
        # Create publisher
        publisher = ESASSClawHubPublisher(
            formatter=self.formatter,
            client=self.clawhub,
            require_confidence=self.config.publish_confidence_threshold,
            require_support=self.config.publish_support_threshold
        )
        
        published_count = 0
        
        for skill in skills:
            # Check rate limit
            if self._skills_published_today >= self.config.rate_limit_skills_per_day:
                break
            
            # Get source pattern
            pattern = None
            if skill.source_pattern_ids:
                pattern = pattern_map.get(skill.source_pattern_ids[0])
            
            # Human approval check
            if self.config.require_human_approval:
                logger.info(f"Skill {skill.name} awaiting human approval")
                continue
            
            # Publish
            response = publisher.publish_skill(skill, pattern)
            
            if response.result == PublishResult.SUCCESS:
                published_count += 1
                self._skills_published_today += 1
                self.metrics.skills_published += 1
                
                logger.info(f"Published skill: {response.skill_slug} v{response.version}")
                
                if self._on_skill_published:
                    self._on_skill_published(skill, response)
            
            elif response.result == PublishResult.ALREADY_EXISTS:
                logger.debug(f"Skill already exists: {response.skill_slug}")
            
            else:
                self.metrics.publish_failures += 1
                logger.warning(f"Failed to publish {skill.name}: {response.message}")
        
        return published_count
    
    async def _sync_to_openclaw(self) -> None:
        """Sync ClawHub skills to OpenClaw workspace"""
        try:
            # Use clawhub CLI sync
            result = self.clawhub.update(all_skills=True)
            if result:
                logger.info("Synced skills to OpenClaw workspace")
            else:
                logger.warning("Skill sync may have failed")
        except Exception as e:
            logger.error(f"Sync error: {e}")
    
    def _update_rolling_metrics(self, results: dict) -> None:
        """Update rolling average metrics"""
        n = self.metrics.cycles_completed
        
        # Update totals
        self.metrics.events_observed += results["events_processed"]
        self.metrics.patterns_detected += results["patterns_detected"]
        self.metrics.skills_generated += results["skills_generated"]
        
        # Rolling averages
        if n > 0:
            self.metrics.avg_patterns_per_cycle = (
                self.metrics.patterns_detected / n
            )
            self.metrics.avg_skills_per_cycle = (
                self.metrics.skills_generated / n
            )
    
    def get_status(self) -> dict:
        """Get current loop status"""
        return {
            "phase": self.phase.value,
            "running": self._running,
            "metrics": {
                "cycles_completed": self.metrics.cycles_completed,
                "events_observed": self.metrics.events_observed,
                "patterns_detected": self.metrics.patterns_detected,
                "skills_generated": self.metrics.skills_generated,
                "skills_published": self.metrics.skills_published,
                "publish_failures": self.metrics.publish_failures,
                "avg_patterns_per_cycle": round(self.metrics.avg_patterns_per_cycle, 2),
                "avg_skills_per_cycle": round(self.metrics.avg_skills_per_cycle, 2),
                "last_cycle_duration": self.metrics.last_cycle_duration_seconds
            },
            "rate_limits": {
                "skills_published_today": self._skills_published_today,
                "daily_limit": self.config.rate_limit_skills_per_day
            }
        }


# Convenience function for quick setup
def create_recursive_loop(
    observation_hours: int = 24,
    cycle_hours: int = 6,
    auto_publish: bool = True
) -> RecursiveLoopController:
    """Create and configure a recursive loop controller"""
    config = LoopConfig(
        observation_window_hours=observation_hours,
        cycle_interval_hours=cycle_hours,
        auto_publish=auto_publish
    )
    return RecursiveLoopController(config=config)
```

---

## Configuration

### `src/config/settings.py`

```python
"""
Configuration Management for ESASS × OpenClaw Integration
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class ESASSConfig:
    """ESASS observation and analysis settings"""
    enabled: bool = True
    data_dir: str = "./data/esass"
    sample_rate: float = 1.0
    
    # Probes
    tool_probe_enabled: bool = True
    reasoning_probe_enabled: bool = True
    decision_probe_enabled: bool = True
    
    # Pipeline
    buffer_size: int = 100
    flush_interval_seconds: float = 5.0


@dataclass
class OpenClawConfig:
    """OpenClaw integration settings"""
    workspace_dir: str = str(Path.home() / ".openclaw")
    skills_dir: str = "skills"
    config_file: str = "openclaw.json"
    
    # Gateway
    gateway_url: str = "ws://127.0.0.1:18789"
    gateway_token: Optional[str] = None


@dataclass 
class ClawHubConfig:
    """ClawHub registry settings"""
    registry_url: str = "https://clawhub.com"
    token: Optional[str] = None
    
    # Publishing
    auto_bump: str = "patch"
    default_tags: list = field(default_factory=lambda: ["latest", "esass-generated"])


@dataclass
class LoopSettings:
    """Recursive loop timing and thresholds"""
    # Timing
    observation_window_hours: int = 24
    cycle_interval_hours: int = 6
    
    # Detection thresholds
    min_events_for_detection: int = 100
    min_support: int = 10
    min_confidence: float = 0.8
    min_stability_days: int = 7
    
    # Generation
    auto_generate: bool = True
    max_skills_per_cycle: int = 5
    
    # Publishing
    auto_publish: bool = True
    publish_confidence_threshold: float = 0.85
    publish_support_threshold: int = 15
    
    # Safety
    require_human_approval: bool = False
    rate_limit_skills_per_day: int = 10


@dataclass
class IntegrationConfig:
    """Complete integration configuration"""
    esass: ESASSConfig = field(default_factory=ESASSConfig)
    openclaw: OpenClawConfig = field(default_factory=OpenClawConfig)
    clawhub: ClawHubConfig = field(default_factory=ClawHubConfig)
    loop: LoopSettings = field(default_factory=LoopSettings)
    
    @classmethod
    def from_env(cls) -> "IntegrationConfig":
        """Load configuration from environment variables"""
        return cls(
            esass=ESASSConfig(
                enabled=os.environ.get("ESASS_ENABLED", "true").lower() == "true",
                data_dir=os.environ.get("ESASS_DATA_DIR", "./data/esass"),
                sample_rate=float(os.environ.get("ESASS_SAMPLE_RATE", "1.0")),
            ),
            openclaw=OpenClawConfig(
                workspace_dir=os.environ.get(
                    "OPENCLAW_WORKSPACE",
                    str(Path.home() / ".openclaw")
                ),
                gateway_url=os.environ.get(
                    "OPENCLAW_GATEWAY_URL",
                    "ws://127.0.0.1:18789"
                ),
                gateway_token=os.environ.get("OPENCLAW_GATEWAY_TOKEN"),
            ),
            clawhub=ClawHubConfig(
                registry_url=os.environ.get("CLAWHUB_REGISTRY", "https://clawhub.com"),
                token=os.environ.get("CLAWHUB_TOKEN"),
            ),
            loop=LoopSettings(
                observation_window_hours=int(
                    os.environ.get("LOOP_OBSERVATION_HOURS", "24")
                ),
                cycle_interval_hours=int(
                    os.environ.get("LOOP_CYCLE_HOURS", "6")
                ),
                auto_publish=os.environ.get(
                    "LOOP_AUTO_PUBLISH", "true"
                ).lower() == "true",
            )
        )


# Global configuration instance
_config: Optional[IntegrationConfig] = None


def get_config() -> IntegrationConfig:
    """Get global configuration"""
    global _config
    if _config is None:
        _config = IntegrationConfig.from_env()
    return _config


def set_config(config: IntegrationConfig) -> None:
    """Set global configuration"""
    global _config
    _config = config
```

---

## Quick Start Example

### `examples/quick_start.py`

```python
"""
Quick Start: ESASS × OpenClaw × ClawHub Integration

Run this to see the recursive learning loop in action.
"""

import asyncio
from datetime import datetime

# Import integration components
from src.loop.controller import RecursiveLoopController, LoopConfig
from src.bridge.openclaw_hooks import OpenClawESASSBridge, OpenClawEvent, OpenClawEventType


async def main():
    print("=" * 70)
    print("ESASS × OpenClaw × ClawHub - Recursive Learning Loop")
    print("=" * 70)
    print()
    
    # Configure the loop
    config = LoopConfig(
        observation_window_hours=1,  # Short window for demo
        cycle_interval_hours=1,
        min_events_for_detection=10,  # Lower threshold for demo
        min_support=3,
        min_confidence=0.7,
        auto_publish=False,  # Disable for demo
        require_human_approval=False
    )
    
    # Create controller
    controller = RecursiveLoopController(config=config)
    
    # Register callbacks
    controller.on_skill_generated(lambda skill: print(f"✓ Generated: {skill.name}"))
    controller.on_cycle_complete(lambda results: print(f"✓ Cycle complete: {results}"))
    
    print("[1] Simulating OpenClaw events...")
    print("-" * 70)
    
    # Simulate some OpenClaw events
    bridge = controller.bridge
    
    for session_num in range(5):
        session_id = f"demo-session-{session_num}"
        
        # Session start
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SESSION_START,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            channel="telegram"
        ))
        
        # Thinking
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.THINKING_BLOCK,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "content": "I'll check the git status first to see what files have changed",
                "type": "planning"
            }
        ))
        
        # Tool call
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.TOOL_CALL_START,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "call_id": f"call-{session_num}-1",
                "tool_name": "Bash",
                "parameters": {"command": "git status"}
            }
        ))
        
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.TOOL_CALL_COMPLETE,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "call_id": f"call-{session_num}-1",
                "success": True,
                "result": "On branch main\nChanges not staged..."
            }
        ))
        
        # Decision
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.APPROACH_SELECTED,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            data={
                "approach": "stage_and_commit",
                "alternatives": ["commit_all", "stage_selective"],
                "rationale": "User has specific files to commit"
            }
        ))
        
        # Session end
        await bridge.on_event(OpenClawEvent(
            event_type=OpenClawEventType.SESSION_END,
            timestamp=datetime.utcnow(),
            session_id=session_id
        ))
        
        print(f"  Session {session_num + 1}: ✓ Generated git workflow events")
    
    print()
    print("[2] Running learning cycle...")
    print("-" * 70)
    
    # Run one cycle
    results = await controller.run_cycle()
    
    print()
    print("[3] Results")
    print("-" * 70)
    print(f"  Events processed: {results['events_processed']}")
    print(f"  Patterns detected: {results['patterns_detected']}")
    print(f"  Skills generated: {results['skills_generated']}")
    
    print()
    print("[4] Loop Status")
    print("-" * 70)
    status = controller.get_status()
    for key, value in status["metrics"].items():
        print(f"  {key}: {value}")
    
    print()
    print("=" * 70)
    print("Demo complete! In production, the loop runs continuously.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Next Steps

1. **Install dependencies**: `pip install pyyaml`
2. **Set up ClawHub auth**: `clawhub login`
3. **Configure OpenClaw hooks**: Add event emission to agent loop
4. **Run the demo**: `python examples/quick_start.py`
5. **Enable production loop**: Configure and start controller

See `DEPLOYMENT_GUIDE.md` for production deployment instructions.
