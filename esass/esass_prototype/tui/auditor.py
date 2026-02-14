"""ESASS Skill Auditor TUI - Human-in-the-Middle Review Interface."""

from datetime import datetime
from typing import List, Optional

from rich.panel import Panel
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)

from ..config import get_config, get_data_dir
from ..storage.skill_store import SkillStore
from ..storage.log_store import LogStore
from ..storage.pattern_store import PatternStore
from ..models import SkillManifest, PatternDefinition


class SkillListItem(ListItem):
    """Custom ListItem for skills with reactive status."""

    def __init__(self, skill: SkillManifest):
        super().__init__()
        self.skill = skill
        self.label = Label(self._get_display_text())

    def _get_display_text(self) -> Text:
        status = self.skill.validation_status
        if status == "pending":
            style = "yellow"
            status_text = "[P]"
        elif status == "validated":
            style = "green"
            status_text = "[OK]"
        else:
            style = "red"
            status_text = "[X]"

        text = Text()
        text.append(f"{status_text} ", style=f"bold {style}")
        text.append(self.skill.name, style="white")
        return text

    def compose(self) -> ComposeResult:
        yield self.label

    def update_status(self):
        self.label.update(self._get_display_text())


class PatternListItem(ListItem):
    """Custom ListItem for patterns."""

    def __init__(self, pattern: PatternDefinition):
        super().__init__()
        self.pattern = pattern
        self.label = Label(self._get_display_text())

    def _get_display_text(self) -> Text:
        icon = "󰄲 " if self.pattern.skill_candidate else "󰄱 "
        style = "cyan" if self.pattern.skill_candidate else "dim"

        desc = (
            self.pattern.description[:45] + "..."
            if len(self.pattern.description) > 45
            else self.pattern.description
        )

        text = Text()
        text.append(f"{icon} ", style=style)
        text.append(desc, style="white")
        return text

    def compose(self) -> ComposeResult:
        yield self.label


class SkillAuditorApp(App):
    """ESASS Skill Auditor TUI."""

    TITLE = "ESASS Skill Auditor"
    SUB_TITLE = "Human-in-the-Middle Auditing"

    CSS = """
    Screen {
        background: #0f172a;
    }

    Header {
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
    }

    Footer {
        background: #1e293b;
    }

    .pane-container {
        height: 100%;
    }

    .left-panel {
        width: 35%;
        height: 100%;
        border-right: tall #334155;
        padding: 0 1;
    }

    .right-panel {
        width: 65%;
        height: 100%;
        padding: 0 1;
    }

    #skill_list, #pattern_list {
        height: 1fr;
        border: solid #334155;
        background: #1e293b;
    }

    #skill_list ListItem, #pattern_list ListItem {
        padding: 0 1;
    }

    #skill_list ListItem:hover, #pattern_list ListItem:hover {
        background: #334155;
    }

    #skill_list ListItem.--highlight, #pattern_list ListItem.--highlight {
        background: #0ea5e9;
        color: white;
    }

    .detail-container {
        height: 100%;
        border: solid #334155;
        background: #1e293b;
        padding: 1;
    }

    #skill_detail_markdown, #pattern_detail_markdown {
        height: 1fr;
        overflow-y: scroll;
    }

    .list-header {
        padding: 1 0;
        color: #38bdf8;
    }

    Input {
        margin: 1 0;
        border: solid #334155;
        background: #0f172a;
    }

    Input:focus {
        border: double #38bdf8;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }

    #monitor_content {
        padding: 1;
        background: #1e293b;
        border: solid #334155;
    }

    .action-bar {
        height: 3;
        align: center middle;
        background: #1e293b;
        margin-top: 1;
    }

    .btn-approve {
        background: #166534;
        color: white;
    }

    .btn-reject {
        background: #991b1b;
        color: white;
    }
    .action-bar-no-margin {
        height: 3;
        align: center middle;
        background: #1e293b;
        margin-top: 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "approve", "Approve", show=True),
        Binding("A", "approve_all", "Approve All", show=True),
        Binding("r", "reject", "Reject", show=True),
        Binding("g", "generate_skills", "Generate Skills", show=True),
        Binding("f5", "refresh", "Refresh", show=True),
        Binding("s", "toggle_sidebar", "Toggle List", show=False),
    ]

    def __init__(self):
        super().__init__()
        config = get_config()
        data_dir = get_data_dir(config)
        self.skill_store = SkillStore(data_dir)
        self.log_store = LogStore(data_dir)
        self.pattern_store = PatternStore(data_dir)

        self._all_skills: List[SkillManifest] = []
        self._all_patterns: List[PatternDefinition] = []
        self.current_skill: Optional[SkillManifest] = None
        self.current_pattern: Optional[PatternDefinition] = None

    def compose(self) -> ComposeResult:
        # Load initial data
        self._all_skills = self.skill_store.load_all()
        self._all_patterns = self.pattern_store.load_all()

        yield Header()

        with TabbedContent(id="main_tabs"):
            # Skills Tab
            with TabPane("Skills", id="skills_tab"):
                with Horizontal(classes="pane-container"):
                    with Vertical(classes="left-panel"):
                        yield Label(
                            "Skill Discovery",
                            id="skill_list_header",
                            classes="list-header",
                        )
                        yield Input(placeholder="Filter skills...", id="skill_filter")
                        yield ListView(id="skill_list")
                    with Vertical(classes="right-panel"):
                        with Container(classes="detail-container"):
                            yield Markdown(
                                "Select a skill to view details",
                                id="skill_detail_markdown",
                            )
                            with Horizontal(classes="action-bar", id="skill_actions"):
                                yield Button(
                                    "Approve (A)",
                                    variant="success",
                                    id="btn_approve",
                                    classes="btn-approve",
                                )
                                yield Button(
                                    "Reject (R)",
                                    variant="error",
                                    id="btn_reject",
                                    classes="btn-reject",
                                )
                                yield Button(
                                    "Approve All (Shift+A)",
                                    variant="primary",
                                    id="btn_approve_all",
                                )

            # Patterns Tab
            with TabPane("Patterns", id="patterns_tab"):
                with Horizontal(classes="pane-container"):
                    with Vertical(classes="left-panel"):
                        yield Label(
                            "Pattern Archeology",
                            id="pattern_list_header",
                            classes="list-header",
                        )
                        yield Input(
                            placeholder="Filter patterns...", id="pattern_filter"
                        )
                        yield ListView(id="pattern_list")
                    with Vertical(classes="right-panel"):
                        with Container(classes="detail-container"):
                            yield Markdown(
                                "Select a pattern to view details",
                                id="pattern_detail_markdown",
                            )

            # Verified Tab
            with TabPane("Verified", id="verified_tab"):
                with Horizontal(classes="pane-container"):
                    with Vertical(classes="left-panel"):
                        yield Label(
                            "Crystallized Skills",
                            id="verified_list_header",
                            classes="list-header",
                        )
                        yield Input(
                            placeholder="Search verified...", id="verified_filter"
                        )
                        yield ListView(id="verified_list")
                        with Horizontal(classes="action-bar-no-margin"):
                            yield Button(
                                "Generate All (G)",
                                variant="primary",
                                id="btn_generate_verified",
                            )
                    with Vertical(classes="right-panel"):
                        with Container(classes="detail-container"):
                            yield Markdown(
                                "Select a verified skill to view manifest",
                                id="verified_detail_markdown",
                            )

            # Monitor Tab
            with TabPane("Monitor", id="monitor_tab"):
                with VerticalScroll():
                    yield Static(id="monitor_content")

        yield Footer()

    def on_mount(self) -> None:
        """Populate lists on mount."""
        self._refresh_skill_list()
        self._refresh_verified_list()
        self._refresh_pattern_list()
        self._update_monitor_view()
        # Single skill actions hidden initially, but bulk actions can be visible
        self.query_one("#btn_approve").visible = False
        self.query_one("#btn_reject").visible = False

    def _refresh_skill_list(self, filter_text: str = "") -> None:
        """Re-populate the skill list."""
        list_view = self.query_one("#skill_list", ListView)
        list_view.clear()

        # Sort: pending first, then by name
        status_priority = {"pending": 0, "validated": 1, "rejected": 2}

        filtered = [
            s
            for s in self._all_skills
            if filter_text.lower() in s.name.lower()
            or filter_text.lower() in s.description.lower()
        ]

        filtered.sort(
            key=lambda s: (status_priority.get(s.validation_status, 3), s.name)
        )

        for skill in filtered:
            list_view.append(SkillListItem(skill))

        pending_count = sum(
            1 for s in self._all_skills if s.validation_status == "pending"
        )
        self.query_one("#skill_list_header", Label).update(
            f"Skill Discovery ({pending_count} Pending)"
        )

    def _refresh_pattern_list(self, filter_text: str = "") -> None:
        """Re-populate the pattern list."""
        list_view = self.query_one("#pattern_list", ListView)
        list_view.clear()

        filtered = [
            p
            for p in self._all_patterns
            if filter_text.lower() in p.description.lower()
        ]

        for pattern in filtered:
            list_view.append(PatternListItem(pattern))

        candidate_count = sum(1 for p in self._all_patterns if p.skill_candidate)
        self.query_one("#pattern_list_header", Label).update(
            f"Pattern Archeology ({candidate_count} Candidates)"
        )

    def _refresh_verified_list(self, filter_text: str = "") -> None:
        """Re-populate the verified skill list."""
        list_view = self.query_one("#verified_list", ListView)
        list_view.clear()

        verified = [s for s in self._all_skills if s.validation_status == "validated"]

        filtered = [
            s
            for s in verified
            if filter_text.lower() in s.name.lower()
            or filter_text.lower() in s.description.lower()
        ]

        filtered.sort(key=lambda s: s.name)

        for skill in filtered:
            list_view.append(SkillListItem(skill))

        self.query_one("#verified_list_header", Label).update(
            f"Crystallized Skills ({len(verified)})"
        )

    @on(Input.Changed, "#skill_filter")
    def on_skill_filter_changed(self, event: Input.Changed) -> None:
        self._refresh_skill_list(event.value)

    @on(Input.Changed, "#pattern_filter")
    def on_pattern_filter_changed(self, event: Input.Changed) -> None:
        self._refresh_pattern_list(event.value)

    @on(Input.Changed, "#verified_filter")
    def on_verified_filter_changed(self, event: Input.Changed) -> None:
        self._refresh_verified_list(event.value)

    @on(ListView.Selected, "#skill_list")
    def on_skill_selected(self, event: ListView.Selected):
        """Handle skill selection."""
        item = event.item
        if isinstance(item, SkillListItem):
            self.current_skill = item.skill
            self._update_skill_detail()
            self.query_one("#btn_approve").visible = True
            self.query_one("#btn_reject").visible = True

    @on(ListView.Selected, "#pattern_list")
    def on_pattern_selected(self, event: ListView.Selected):
        """Handle pattern selection."""
        item = event.item
        if isinstance(item, PatternListItem):
            self.current_pattern = item.pattern
            self._update_pattern_detail()

    @on(ListView.Selected, "#verified_list")
    def on_verified_selected(self, event: ListView.Selected):
        """Handle verified skill selection."""
        item = event.item
        if isinstance(item, SkillListItem):
            self.current_skill = item.skill
            self._update_verified_detail()

    def _update_skill_detail(self):
        """Update the skill detail panel with Markdown."""
        if not self.current_skill:
            return

        skill = self.current_skill

        status_color = (
            "yellow"
            if skill.validation_status == "pending"
            else ("green" if skill.validation_status == "validated" else "red")
        )

        # Triggers section
        triggers_md = ""
        for t in skill.triggers:
            if hasattr(t, "trigger_type"):
                triggers_md += f"* **{t.trigger_type}**: `{t.pattern}`\n"
            else:
                triggers_md += f"* {t}\n"

        capabilities = (
            ", ".join([f"`{c}`" for c in skill.capabilities])
            if skill.capabilities
            else "*None*"
        )

        status_val = skill.validation_status.upper()
        status_md = (
            f"**Status**: <span style='color: {status_color}; "
            f"font-weight: bold;'>{status_val}</span>"
        )

        md = f"""
# {skill.name}
{status_md}
**Version**: `{skill.version}` | **Genesis**: `{skill.genesis_type}`

### Description
{skill.description}

### Triggers
{triggers_md}

### Capabilities
{capabilities}

### Implementation Summary
```text
{skill.implementation_summary}
```

### Statistics
* **Usage Count**: {skill.usage_count}
* **Success Rate**: {skill.success_rate:.1%}
* **ID**: `{skill.skill_id}`
* **Created**: {skill.created_at}

---
*Press **A** to Approve or **R** to Reject*
"""
        self.query_one("#skill_detail_markdown", Markdown).update(md)

    def _update_pattern_detail(self):
        """Update the pattern detail panel."""
        if not self.current_pattern:
            return

        p = self.current_pattern

        seq_md = "\n".join([f"{i + 1}. `{step}`" for i, step in enumerate(p.sequence)])

        md = f"""
# Pattern Details
**ID**: `{p.pattern_id}`
**Candidacy**: {"✅ **Skill Candidate**" if p.skill_candidate else "❌ Not a candidate"}

### Description
{p.description}

### Metrics
| Metric | Value |
|--------|-------|
| Support | {p.support} |
| Confidence | {p.confidence:.1%} |
| Stability | {p.stability_days} days |

### Event Sequence
{seq_md}

### Timeline
* **First Seen**: {p.first_seen}
* **Last Seen**: {p.last_seen}

### Tags
{", ".join([f"`{t}`" for t in p.tags]) if p.tags else "*None*"}
"""
        self.query_one("#pattern_detail_markdown", Markdown).update(md)

    def _update_monitor_view(self):
        """Update the monitoring dashboard view."""
        log_stats = self.log_store.get_stats()

        pending = sum(1 for s in self._all_skills if s.validation_status == "pending")
        validated = sum(
            1 for s in self._all_skills if s.validation_status == "validated"
        )
        rejected = sum(1 for s in self._all_skills if s.validation_status == "rejected")

        content = f"""
[bold cyan]ESASS SYSTEM MONITOR[/bold cyan]
{"━" * 40}

[bold]Skill Statistics[/bold]
  Total Skills:   {len(self._all_skills)}
  [yellow]Pending:        {pending}[/yellow]
  [green]Validated:      {validated}[/green]
  [red]Rejected:       {rejected}[/red]

[bold]Pattern Statistics[/bold]
  Total Patterns: {len(self._all_patterns)}
  Candidates:     {sum(1 for p in self._all_patterns if p.skill_candidate)}

[bold]Log Statistics[/bold]
  Total Events:   {log_stats.get("total_entries", 0)}
  Total Sessions: {log_stats.get("total_sessions", 0)}

[bold]Environment[/bold]
  Data Dir:       {self.skill_store.data_dir}
  Last Refresh:   {datetime.now().strftime("%H:%M:%S")}
"""
        self.query_one("#monitor_content", Static).update(
            Panel(content, border_style="blue")
        )

    def action_approve(self):
        """Approve the current skill."""
        if self.current_skill and self.query_one("#main_tabs").active == "skills_tab":
            self.skill_store.update_validation_status(
                self.current_skill.skill_id, "validated"
            )
            self.current_skill.validation_status = "validated"
            self.notify(f"APPROVED: {self.current_skill.name}", severity="information")

            # Update the list item without refreshing the whole list
            for item in self.query_one("#skill_list").children:
                if (
                    isinstance(item, SkillListItem)
                    and item.skill.skill_id == self.current_skill.skill_id
                ):
                    item.update_status()
                    break

            self._update_skill_detail()
            self._update_monitor_view()

    def action_reject(self):
        """Reject the current skill."""
        if self.current_skill and self.query_one("#main_tabs").active == "skills_tab":
            self.skill_store.update_validation_status(
                self.current_skill.skill_id, "rejected"
            )
            self.current_skill.validation_status = "rejected"
            self.notify(f"REJECTED: {self.current_skill.name}", severity="warning")

            # Update the list item
            for item in self.query_one("#skill_list").children:
                if (
                    isinstance(item, SkillListItem)
                    and item.skill.skill_id == self.current_skill.skill_id
                ):
                    item.update_status()
                    break

            self._update_skill_detail()
            self._update_monitor_view()

    def action_refresh(self):
        """Refresh all data from disk."""
        self._all_skills = self.skill_store.load_all()
        self._all_patterns = self.pattern_store.load_all()
        self._refresh_skill_list(self.query_one("#skill_filter").value)
        self._refresh_pattern_list(self.query_one("#pattern_filter").value)
        self._update_monitor_view()
        self.notify("Data refreshed from disk")

    def action_approve_all(self):
        """Approve all skills in the currently filtered list."""
        if self.query_one("#main_tabs").active != "skills_tab":
            return

        list_view = self.query_one("#skill_list", ListView)
        pending_items = [
            item
            for item in list_view.children
            if isinstance(item, SkillListItem)
            and item.skill.validation_status == "pending"
        ]

        if not pending_items:
            self.notify(
                "No pending skills to approve in current view", severity="warning"
            )
            return

        count = len(pending_items)
        for item in pending_items:
            self.skill_store.update_validation_status(item.skill.skill_id, "validated")
            item.skill.validation_status = "validated"
            item.update_status()

        self.notify(f"BULK APPROVED: {count} skills", severity="information")
        self._update_monitor_view()
        self._refresh_skill_list(self.query_one("#skill_filter").value)

    @on(Button.Pressed, "#btn_approve")
    def on_approve_pressed(self):
        self.action_approve()

    @on(Button.Pressed, "#btn_reject")
    def on_reject_pressed(self):
        self.action_reject()

    @on(Button.Pressed, "#btn_approve_all")
    def on_approve_all_pressed(self):
        self.action_approve_all()

    @on(Button.Pressed, "#btn_generate_verified")
    def on_generate_verified_pressed(self):
        self.action_generate_skills()

    def action_generate_skills(self):
        """Convert validated SkillManifests to Claude Project SKILL.md files."""
        validated_skills = [
            s for s in self._all_skills if s.validation_status == "validated"
        ]

        if not validated_skills:
            self.notify("No validated skills found to generate", severity="warning")
            return

        try:
            from esass_prototype.adapters.claude_formatter import ClaudeSkillFormatter

            formatter = ClaudeSkillFormatter(output_dir=".claude/skills")

            # Map patterns for formatter
            pattern_map = {p.pattern_id: p for p in self._all_patterns}

            paths = formatter.batch_convert(validated_skills, patterns=pattern_map)
            self.notify(
                f"SUCCESS: Generated {len(paths)} skills in .claude/skills",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Generation error: {str(e)}", severity="error")

    def _update_verified_detail(self):
        """Update manifest preview for verified skills."""
        if not self.current_skill:
            return

        try:
            from esass_prototype.adapters.claude_formatter import ClaudeSkillFormatter

            formatter = ClaudeSkillFormatter()
            pattern = None
            if self.current_skill.source_pattern_ids:
                pattern_id = self.current_skill.source_pattern_ids[0]
                pattern = next(
                    (p for p in self._all_patterns if p.pattern_id == pattern_id), None
                )

            # Use raw markdown for preview
            content = formatter.format_skill(self.current_skill, pattern)
            self.query_one("#verified_detail_markdown", Markdown).update(content)
        except Exception as e:
            self.query_one("#verified_detail_markdown", Markdown).update(
                f"Error generating preview: {e}"
            )


if __name__ == "__main__":
    app = SkillAuditorApp()
    app.run()
