import re
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ParsedEvent:
    type: str  # 'tool_call', 'thinking', 'response', 'decision'
    content: str
    metadata: Dict[str, Any]


class StreamParser:
    """
    Parses output stream from the agent to detect ESASS events.
    This uses regex heuristics since we are intercepting stdout/pty.
    """

    def __init__(self):
        self.buffer = ""
        # Regex patterns for common agent outputs (Claude Code / Open Code Interpreter)
        self.patterns = [
            (r"Tool Call: (\w+)", "tool_call_start"),
            (r"Thinking: (.+)", "thinking"),
            (r"Decision: (.+)", "decision"),
        ]

    def parse(self, chunk: str) -> List[ParsedEvent]:
        """
        Parse a chunk of text and return detected events.
        Note: This is a simplified parser. Robust parsing requires
        handling split lines and ANSI codes.
        """
        events = []
        # Strip ANSI codes for regex matching
        clean_chunk = self._strip_ansi(chunk)
        # print(f"DEBUG: chunk={repr(chunk)} clean={repr(clean_chunk)}")

        for pattern, event_type in self.patterns:
            match = re.search(pattern, clean_chunk)
            if match:
                content = match.group(1) if match.groups() else clean_chunk.strip()
                events.append(ParsedEvent(event_type, content, {}))

        return events

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences."""
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)
