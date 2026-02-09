from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    ListView,
    ListItem,
    Static,
    Label,
    TabbedContent,
    TabPane,
    DataTable,
)
from textual.binding import Binding
from textual import on

from ..config import get_config, get_data_dir
from ..storage.skill_store import SkillStore
from ..storage.log_store import LogStore
from ..storage.pattern_store import PatternStore
from ..models import SkillManifest, PatternDefinition


class SkillItem(ListItem):
    """A list item representing a skill."""

    def __init__(self, skill: SkillManifest):
        super().__init__()
        self.skill = skill

    def compose(self) -> ComposeResult:
        status_icon = (
            "⏳"
            if self.skill.validation_status == "pending"
            else ("✅" if self.skill.validation_status == "validated" else "❌")
        )
        yield Label(f"{status_icon} {self.skill.name}")


class SkillDetail(Static):
    """A widget to display skill details."""

    def update_skill(self, skill: SkillManifest):
        status_color = (
            "yellow"
            if skill.validation_status == "pending"
            else ("green" if skill.validation_status == "validated" else "red")
        )

        content = f"""
# {skill.name}
**Status:** [{status_color}]{skill.validation_status}[/]
**ID:** {skill.skill_id}
**Created:** {skill.created_at}

## Description
{skill.description}

## Implementation Summary
{skill.implementation_summary}

## Triggers
{", ".join(skill.triggers)}

## Capabilities
{", ".join(skill.capabilities)}

## Tags
{", ".join(skill.tags)}
"""
        self.update(content)


class PatternItem(ListItem):
    """A list item representing a pattern."""

    def __init__(self, pattern: PatternDefinition):
        super().__init__()
        self.pattern = pattern

    def compose(self) -> ComposeResult:
        candidate_icon = "⭐" if self.pattern.skill_candidate else "•"
        yield Label(f"{candidate_icon} {self.pattern.description}")


class PatternDetail(Static):
    """A widget to display pattern details."""

    def update_pattern(self, pattern: PatternDefinition):
        candidate_status = "[green]YES[/]" if pattern.skill_candidate else "[red]NO[/]"

        content = f"""
# Pattern Details
**Description:** {pattern.description}
**ID:** {pattern.pattern_id}
**Is Skill Candidate:** {candidate_status}

## Metrics
- **Support:** {pattern.support}
- **Confidence:** {pattern.confidence:.1%}
- **Stability:** {pattern.stability_days} days

## Event Sequence
"""
        for i, step in enumerate(pattern.sequence, 1):
            content += f"{i}. {step}\n"

        content += f"""
## Metadata
- **First Seen:** {pattern.first_seen}
- **Last Seen:** {pattern.last_seen}
"""
        self.update(content)


class MonitoringDashboard(VerticalScroll):
    """Aggregate statistics and health metrics."""

    def __init__(
        self, skill_store: SkillStore, log_store: LogStore, pattern_store: PatternStore
    ):
        super().__init__()
        self.skill_store = skill_store
        self.log_store = log_store
        self.pattern_store = pattern_store

    def on_mount(self):
        self.update_stats()

    def update_stats(self):
        skill_stats = self.skill_store.get_stats()
        log_stats = self.log_store.get_stats()
        pattern_stats = self.pattern_store.get_stats()

        summary = f"""
# ESASS System Monitoring

## Pattern Discovery
- **Total Patterns:** {pattern_stats.get("total_patterns", 0)}
- **Skill Candidates:** {pattern_stats.get("skill_candidates", 0)}
- **Avg Confidence:** {pattern_stats.get("avg_confidence", 0):.1%}

## Skill Evolution
- **Total Skills:** {skill_stats.get("total_skills", 0)}
- **Pending Audit:** {skill_stats.get("by_status", {}).get("pending", 0)}
- **Validated:** {skill_stats.get("by_status", {}).get("validated", 0)}

## Observation Fidelity
- **Total Events:** {log_stats.get("total_entries", 0)}
- **Sessions Tracked:** {log_stats.get("total_sessions", 0)}
"""
        self.query_one("#monitor_summary").update(summary)

        # Update capabilities table
        table = self.query_one(DataTable)
        table.clear()
        table.add_columns("Capability", "Count")

        all_skills = self.skill_store.load_all()
        cap_counts = {}
        for s in all_skills:
            for cap in s.capabilities:
                cap_counts[cap] = cap_counts.get(cap, 0) + 1

        for cap, count in sorted(cap_counts.items(), key=lambda x: x[1], reverse=True):
            table.add_row(cap, str(count))

    def compose(self) -> ComposeResult:
        yield Static(id="monitor_summary")
        yield Label("\n[bold]Skill Distribution by Capability[/]")
        yield DataTable()


class SkillAuditorApp(App):
    """ESASS Skill Auditor TUI."""

    TITLE = "ESASS Skill Auditor"
    SUB_TITLE = "Human-in-the-Middle Auditing & Monitoring"

    CSS = """
    Screen {
        background: $surface;
    }
    
    #main_container, #pattern_container {
        height: 100%;
    }
    
    .sidebar {
        width: 30%;
        height: 100%;
        border-right: tall blue;
        background: $surface;
    }
    
    .content {
        width: 70%;
        height: 100%;
        padding: 1;
    }

    ListView {
        background: $surface;
    }

    SkillDetail, PatternDetail {
        padding: 1;
        background: $boost;
        border: round blue;
    }
    
    MonitoringDashboard {
        padding: 1;
    }
    
    DataTable {
        height: auto;
        max-height: 20;
        border: round blue;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "approve", "Approve Skill", show=True, key_display="A"),
        Binding("r", "reject", "Reject Skill", show=True, key_display="R"),
        Binding("p", "pending", "Set Pending", show=True, key_display="P"),
        Binding("refresh", "refresh", "Refresh Data", show=True, key_display="F5"),
    ]

    def __init__(self):
        super().__init__()
        config = get_config()
        data_dir = get_data_dir(config)
        self.skill_store = SkillStore(data_dir)
        self.log_store = LogStore(data_dir)
        self.pattern_store = PatternStore(data_dir)
        self.current_skill: Optional[SkillManifest] = None
        self.current_pattern: Optional[PatternDefinition] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Skill Auditing", id="audit_tab"):
                with Horizontal(id="main_container"):
                    with Vertical(classes="sidebar"):
                        yield Label("[bold]Skills[/]")
                        yield ListView(id="skill_list")
                    with Vertical(classes="content"):
                        yield SkillDetail(id="skill_detail")
            with TabPane("Pattern Discovery", id="pattern_tab"):
                with Horizontal(id="pattern_container"):
                    with Vertical(classes="sidebar"):
                        yield Label("[bold]Detected Patterns[/]")
                        yield ListView(id="pattern_list")
                    with Vertical(classes="content"):
                        yield PatternDetail(id="pattern_detail")
            with TabPane("System Monitoring", id="monitor_tab"):
                yield MonitoringDashboard(
                    self.skill_store, self.log_store, self.pattern_store
                )
        yield Footer()

    def on_mount(self):
        self.refresh_skill_list()
        self.refresh_pattern_list()

    def refresh_skill_list(self):
        skill_list = self.query_one("#skill_list", ListView)
        skill_list.clear()

        skills = self.skill_store.load_all()
        for skill in skills:
            skill_list.append(SkillItem(skill))

    def refresh_pattern_list(self):
        pattern_list = self.query_one("#pattern_list", ListView)
        pattern_list.clear()

        patterns = self.pattern_store.load_all()
        for pattern in patterns:
            pattern_list.append(PatternItem(pattern))

    @on(ListView.Selected)
    def on_item_selected(self, event: ListView.Selected):
        if isinstance(event.item, SkillItem):
            self.current_skill = event.item.skill
            self.query_one("#skill_detail", SkillDetail).update_skill(
                self.current_skill
            )
        elif isinstance(event.item, PatternItem):
            self.current_pattern = event.item.pattern
            self.query_one("#pattern_detail", PatternDetail).update_pattern(
                self.current_pattern
            )

    def action_approve(self):
        if self.current_skill:
            self.skill_store.update_validation_status(
                self.current_skill.skill_id, "validated"
            )
            self.notify(f"Skill '{self.current_skill.name}' approved ✅")
            self._reload_and_refresh()

    def action_reject(self):
        if self.current_skill:
            self.skill_store.update_validation_status(
                self.current_skill.skill_id, "rejected"
            )
            self.notify(f"Skill '{self.current_skill.name}' rejected ❌")
            self._reload_and_refresh()

    def action_pending(self):
        if self.current_skill:
            self.skill_store.update_validation_status(
                self.current_skill.skill_id, "pending"
            )
            self.notify(f"Skill '{self.current_skill.name}' set to pending ⏳")
            self._reload_and_refresh()

    def action_refresh(self):
        self._reload_and_refresh()
        self.notify("Data refreshed")

    def _reload_and_refresh(self):
        # Refresh skills
        skill_list = self.query_one("#skill_list", ListView)
        s_index = skill_list.index
        self.refresh_skill_list()
        if s_index is not None:
            skill_list.index = s_index

        # Refresh patterns
        pattern_list = self.query_one("#pattern_list", ListView)
        p_index = pattern_list.index
        self.refresh_pattern_list()
        if p_index is not None:
            pattern_list.index = p_index

        # Update monitoring tab if it exists
        try:
            self.query_one(MonitoringDashboard).update_stats()
        except Exception:
            pass


if __name__ == "__main__":
    app = SkillAuditorApp()
    app.run()
