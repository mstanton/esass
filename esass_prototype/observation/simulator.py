"""
Event simulator for generating realistic synthetic observation data.

Simulates 5 common Claude Code interaction scenarios to demonstrate
pattern detection and skill generation capabilities.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import uuid4
import random

from esass_prototype.models import (
    LogEntry,
    EventType,
    create_reasoning_event,
    create_tool_usage_event,
    create_decision_event
)


class EventSimulator:
    """
    Generate realistic synthetic observation data mimicking Claude Code interactions.

    Scenarios:
    1. Git workflow (commit changes)
    2. Code analysis (understand codebase structure)
    3. Bug fix (identify and fix error)
    4. Documentation update (update README)
    5. Test writing (create unit tests)
    """

    SCENARIOS = [
        "git_workflow",
        "code_analysis",
        "bug_fix",
        "documentation_update",
        "test_writing"
    ]

    def __init__(self, seed: int = None):
        """
        Initialize simulator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)

    def generate_session(
        self,
        scenario: str,
        base_time: datetime,
        session_id: str = None
    ) -> List[LogEntry]:
        """
        Generate a complete session for a scenario.

        Args:
            scenario: Scenario type (from SCENARIOS)
            base_time: Starting timestamp
            session_id: Optional session ID (generates if None)

        Returns:
            List of LogEntry objects for the session
        """
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")

        session_id = session_id or str(uuid4())

        # Route to scenario-specific generator
        if scenario == "git_workflow":
            return self._git_workflow_sequence(session_id, base_time)
        elif scenario == "code_analysis":
            return self._code_analysis_sequence(session_id, base_time)
        elif scenario == "bug_fix":
            return self._bug_fix_sequence(session_id, base_time)
        elif scenario == "documentation_update":
            return self._documentation_update_sequence(session_id, base_time)
        elif scenario == "test_writing":
            return self._test_writing_sequence(session_id, base_time)

    def _git_workflow_sequence(
        self,
        session_id: str,
        start_time: datetime
    ) -> List[LogEntry]:
        """
        Generate git workflow event sequence.

        Pattern: reasoning → git status → git diff → decision → git add → git commit
        """
        entries = []
        current_time = start_time

        # Event 1: Reasoning - user wants to commit changes
        entry1 = create_reasoning_event(
            statement="User wants to commit changes to repository",
            confidence=0.95,
            session_id=session_id,
            tags=["git", "commit", "workflow"]
        )
        entry1.timestamp = current_time.isoformat()
        entries.append(entry1)
        current_time += timedelta(seconds=random.randint(2, 5))

        # Event 2: Tool usage - git status
        entry2 = create_tool_usage_event(
            tool_name="Bash",
            parameters={"command": "git status"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["git", "status"],
            caused_by=[entry1.entry_id]
        )
        entry2.timestamp = current_time.isoformat()
        entries.append(entry2)
        current_time += timedelta(seconds=random.randint(3, 6))

        # Event 3: Tool usage - git diff
        entry3 = create_tool_usage_event(
            tool_name="Bash",
            parameters={"command": "git diff"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["git", "diff"],
            caused_by=[entry2.entry_id]
        )
        entry3.timestamp = current_time.isoformat()
        entries.append(entry3)
        current_time += timedelta(seconds=random.randint(5, 10))

        # Event 4: Decision - select files to stage
        entry4 = create_decision_event(
            decision="Add all modified files to staging area",
            confidence=0.9,
            session_id=session_id,
            tags=["git", "decision", "staging"],
            caused_by=[entry3.entry_id]
        )
        entry4.timestamp = current_time.isoformat()
        entries.append(entry4)
        current_time += timedelta(seconds=random.randint(2, 4))

        # Event 5: Tool usage - git add
        entry5 = create_tool_usage_event(
            tool_name="Bash",
            parameters={"command": "git add ."},
            outcome_assessment="success",
            session_id=session_id,
            tags=["git", "add"],
            caused_by=[entry4.entry_id]
        )
        entry5.timestamp = current_time.isoformat()
        entries.append(entry5)
        current_time += timedelta(seconds=random.randint(3, 5))

        # Event 6: Tool usage - git commit
        commit_msg = random.choice([
            "Update implementation",
            "Fix bug in feature",
            "Add new functionality",
            "Refactor code structure"
        ])
        entry6 = create_tool_usage_event(
            tool_name="Bash",
            parameters={"command": f'git commit -m "{commit_msg}"'},
            outcome_assessment="success",
            session_id=session_id,
            tags=["git", "commit"],
            caused_by=[entry5.entry_id]
        )
        entry6.timestamp = current_time.isoformat()
        entries.append(entry6)

        return entries

    def _code_analysis_sequence(
        self,
        session_id: str,
        start_time: datetime
    ) -> List[LogEntry]:
        """
        Generate code analysis event sequence.

        Pattern: reasoning → glob files → read files → reasoning → decision → output
        """
        entries = []
        current_time = start_time

        # Event 1: Reasoning - understand codebase
        entry1 = create_reasoning_event(
            statement="Need to understand codebase structure and key components",
            confidence=0.92,
            session_id=session_id,
            tags=["analysis", "codebase", "exploration"]
        )
        entry1.timestamp = current_time.isoformat()
        entries.append(entry1)
        current_time += timedelta(seconds=random.randint(2, 4))

        # Event 2: Tool usage - glob for files
        entry2 = create_tool_usage_event(
            tool_name="Glob",
            parameters={"pattern": "**/*.py"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["search", "files", "python"],
            caused_by=[entry1.entry_id]
        )
        entry2.timestamp = current_time.isoformat()
        entries.append(entry2)
        current_time += timedelta(seconds=random.randint(3, 6))

        # Event 3: Tool usage - read multiple files
        entry3 = create_tool_usage_event(
            tool_name="Read",
            parameters={"file_paths": ["models.py", "config.py", "main.py"]},
            outcome_assessment="success",
            session_id=session_id,
            tags=["read", "files", "analysis"],
            caused_by=[entry2.entry_id]
        )
        entry3.timestamp = current_time.isoformat()
        entries.append(entry3)
        current_time += timedelta(seconds=random.randint(8, 15))

        # Event 4: Reasoning - identify patterns
        entry4 = create_reasoning_event(
            statement="Identified key architectural patterns: MVC structure with modular design",
            confidence=0.88,
            session_id=session_id,
            tags=["analysis", "patterns", "architecture"],
            caused_by=[entry3.entry_id]
        )
        entry4.timestamp = current_time.isoformat()
        entries.append(entry4)
        current_time += timedelta(seconds=random.randint(5, 10))

        # Event 5: Decision - summarize findings
        entry5 = create_decision_event(
            decision="Provide structured analysis with component breakdown",
            confidence=0.93,
            session_id=session_id,
            tags=["decision", "output", "summary"],
            caused_by=[entry4.entry_id]
        )
        entry5.timestamp = current_time.isoformat()
        entries.append(entry5)

        return entries

    def _bug_fix_sequence(
        self,
        session_id: str,
        start_time: datetime
    ) -> List[LogEntry]:
        """
        Generate bug fix event sequence.

        Pattern: reasoning → grep error → read files → reasoning → edit → test
        """
        entries = []
        current_time = start_time

        # Event 1: Reasoning - error reported
        error_msg = random.choice([
            "AttributeError in data processing",
            "IndexError in list operation",
            "TypeError in function call",
            "ValueError in validation logic"
        ])
        entry1 = create_reasoning_event(
            statement=f"User reports: {error_msg}",
            confidence=0.96,
            session_id=session_id,
            tags=["bug", "error", "diagnosis"]
        )
        entry1.timestamp = current_time.isoformat()
        entries.append(entry1)
        current_time += timedelta(seconds=random.randint(2, 4))

        # Event 2: Tool usage - grep for error location
        entry2 = create_tool_usage_event(
            tool_name="Grep",
            parameters={"pattern": error_msg.split()[0], "output_mode": "files_with_matches"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["search", "grep", "debugging"],
            caused_by=[entry1.entry_id]
        )
        entry2.timestamp = current_time.isoformat()
        entries.append(entry2)
        current_time += timedelta(seconds=random.randint(3, 5))

        # Event 3: Tool usage - read relevant files
        entry3 = create_tool_usage_event(
            tool_name="Read",
            parameters={"file_path": "src/module.py"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["read", "file", "analysis"],
            caused_by=[entry2.entry_id]
        )
        entry3.timestamp = current_time.isoformat()
        entries.append(entry3)
        current_time += timedelta(seconds=random.randint(5, 10))

        # Event 4: Reasoning - identify root cause
        entry4 = create_reasoning_event(
            statement="Root cause: off-by-one error in loop boundary condition",
            confidence=0.91,
            session_id=session_id,
            tags=["diagnosis", "root-cause", "logic"],
            caused_by=[entry3.entry_id]
        )
        entry4.timestamp = current_time.isoformat()
        entries.append(entry4)
        current_time += timedelta(seconds=random.randint(3, 6))

        # Event 5: Tool usage - edit file
        entry5 = create_tool_usage_event(
            tool_name="Edit",
            parameters={"file_path": "src/module.py", "change": "Fix loop boundary"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["edit", "fix", "code"],
            caused_by=[entry4.entry_id]
        )
        entry5.timestamp = current_time.isoformat()
        entries.append(entry5)
        current_time += timedelta(seconds=random.randint(4, 7))

        # Event 6: Tool usage - run tests
        entry6 = create_tool_usage_event(
            tool_name="Bash",
            parameters={"command": "pytest tests/"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["test", "verification", "pytest"],
            caused_by=[entry5.entry_id]
        )
        entry6.timestamp = current_time.isoformat()
        entries.append(entry6)

        return entries

    def _documentation_update_sequence(
        self,
        session_id: str,
        start_time: datetime
    ) -> List[LogEntry]:
        """
        Generate documentation update event sequence.

        Pattern: reasoning → read current docs → decision → edit → review
        """
        entries = []
        current_time = start_time

        # Event 1: Reasoning - documentation needed
        entry1 = create_reasoning_event(
            statement="User requests documentation update for new features",
            confidence=0.94,
            session_id=session_id,
            tags=["documentation", "update", "readme"]
        )
        entry1.timestamp = current_time.isoformat()
        entries.append(entry1)
        current_time += timedelta(seconds=random.randint(2, 4))

        # Event 2: Tool usage - read current README
        entry2 = create_tool_usage_event(
            tool_name="Read",
            parameters={"file_path": "README.md"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["read", "documentation", "readme"],
            caused_by=[entry1.entry_id]
        )
        entry2.timestamp = current_time.isoformat()
        entries.append(entry2)
        current_time += timedelta(seconds=random.randint(4, 8))

        # Event 3: Decision - what to update
        entry3 = create_decision_event(
            decision="Add new features section and update installation instructions",
            confidence=0.89,
            session_id=session_id,
            tags=["decision", "content", "structure"],
            caused_by=[entry2.entry_id]
        )
        entry3.timestamp = current_time.isoformat()
        entries.append(entry3)
        current_time += timedelta(seconds=random.randint(3, 5))

        # Event 4: Tool usage - edit README
        entry4 = create_tool_usage_event(
            tool_name="Edit",
            parameters={"file_path": "README.md", "change": "Add features section"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["edit", "documentation", "markdown"],
            caused_by=[entry3.entry_id]
        )
        entry4.timestamp = current_time.isoformat()
        entries.append(entry4)
        current_time += timedelta(seconds=random.randint(5, 10))

        # Event 5: Reasoning - review changes
        entry5 = create_reasoning_event(
            statement="Documentation now clearly explains new features and updated workflow",
            confidence=0.90,
            session_id=session_id,
            tags=["review", "validation", "documentation"],
            caused_by=[entry4.entry_id]
        )
        entry5.timestamp = current_time.isoformat()
        entries.append(entry5)

        return entries

    def _test_writing_sequence(
        self,
        session_id: str,
        start_time: datetime
    ) -> List[LogEntry]:
        """
        Generate test writing event sequence.

        Pattern: reasoning → read code → decision → write tests → run tests
        """
        entries = []
        current_time = start_time

        # Event 1: Reasoning - tests needed
        entry1 = create_reasoning_event(
            statement="Need to write unit tests for new functionality",
            confidence=0.93,
            session_id=session_id,
            tags=["testing", "unit-tests", "coverage"]
        )
        entry1.timestamp = current_time.isoformat()
        entries.append(entry1)
        current_time += timedelta(seconds=random.randint(2, 4))

        # Event 2: Tool usage - read source code
        entry2 = create_tool_usage_event(
            tool_name="Read",
            parameters={"file_path": "src/feature.py"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["read", "source", "analysis"],
            caused_by=[entry1.entry_id]
        )
        entry2.timestamp = current_time.isoformat()
        entries.append(entry2)
        current_time += timedelta(seconds=random.randint(5, 10))

        # Event 3: Decision - test strategy
        entry3 = create_decision_event(
            decision="Write tests for happy path, edge cases, and error handling",
            confidence=0.91,
            session_id=session_id,
            tags=["decision", "strategy", "test-coverage"],
            caused_by=[entry2.entry_id]
        )
        entry3.timestamp = current_time.isoformat()
        entries.append(entry3)
        current_time += timedelta(seconds=random.randint(3, 6))

        # Event 4: Tool usage - write test file
        entry4 = create_tool_usage_event(
            tool_name="Write",
            parameters={"file_path": "tests/test_feature.py", "content": "test functions"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["write", "tests", "pytest"],
            caused_by=[entry3.entry_id]
        )
        entry4.timestamp = current_time.isoformat()
        entries.append(entry4)
        current_time += timedelta(seconds=random.randint(8, 15))

        # Event 5: Tool usage - run tests
        entry5 = create_tool_usage_event(
            tool_name="Bash",
            parameters={"command": "pytest tests/test_feature.py -v"},
            outcome_assessment="success",
            session_id=session_id,
            tags=["test", "execution", "validation"],
            caused_by=[entry4.entry_id]
        )
        entry5.timestamp = current_time.isoformat()
        entries.append(entry5)
        current_time += timedelta(seconds=random.randint(3, 6))

        # Event 6: Reasoning - verify coverage
        entry6 = create_reasoning_event(
            statement="All tests passing with 95% code coverage achieved",
            confidence=0.94,
            session_id=session_id,
            tags=["validation", "coverage", "success"],
            caused_by=[entry5.entry_id]
        )
        entry6.timestamp = current_time.isoformat()
        entries.append(entry6)

        return entries

    def generate_multiple_sessions(
        self,
        count: int,
        days: int,
        scenario_distribution: Dict[str, float] = None
    ) -> List[LogEntry]:
        """
        Generate multiple sessions over a time period.

        Args:
            count: Number of sessions to generate
            days: Number of days to spread sessions across
            scenario_distribution: Optional dict mapping scenario -> probability

        Returns:
            List of all LogEntry objects, sorted by timestamp
        """
        if scenario_distribution is None:
            # Default: equal distribution
            scenario_distribution = {s: 1.0/len(self.SCENARIOS) for s in self.SCENARIOS}

        # Normalize probabilities
        total = sum(scenario_distribution.values())
        scenario_probs = {k: v/total for k, v in scenario_distribution.items()}

        all_entries = []
        start_date = datetime.utcnow() - timedelta(days=days)

        for i in range(count):
            # Select scenario based on distribution
            scenario = random.choices(
                list(scenario_probs.keys()),
                weights=list(scenario_probs.values())
            )[0]

            # Vary timestamps across the time period
            session_time = start_date + timedelta(
                days=random.randint(0, days),
                hours=random.randint(8, 22),  # Realistic work hours
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )

            # Generate session
            entries = self.generate_session(scenario, session_time)
            all_entries.extend(entries)

        # Sort by timestamp
        all_entries.sort(key=lambda e: e.timestamp)

        return all_entries
