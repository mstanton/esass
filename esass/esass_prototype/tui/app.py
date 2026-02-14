from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log, Static, Label
from textual.containers import Vertical
from .process import ProcessManager
from .parser import StreamParser


class PatternWidget(Static):
    """Widget to display detected patterns."""

    def __init__(self):
        super().__init__("Waiting for patterns...")
        self.styles.border = ("heavy", "green")
        self.styles.height = "30%"

    def update_patterns(self, patterns):
        self.update(
            f"Detected Patterns: {len(patterns)}\n"
            + "\n".join([p.description for p in patterns[-5:]])
        )


class TerminalWidget(Log):
    """Widget to display process output."""

    def __init__(self):
        super().__init__()
        self.styles.border = ("heavy", "white")
        self.styles.height = "70%"


class ESASSApp(App):
    """ESASS TUI Application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }
    .left {
        height: 100%;
    }
    .right {
        height: 100%;
        border-left: solid white;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process_manager = None
        self.parser = StreamParser()
        self.patterns = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="left"):
            yield Label("Terminal Output")
            yield TerminalWidget()
        with Vertical(classes="right"):
            yield Label("ESASS Dashboard")
            yield PatternWidget()
            yield Log(id="metrics_log")
        yield Footer()

    def on_mount(self):
        self.process_manager = ProcessManager(
            self.command, on_output=self.on_process_output, on_exit=self.on_process_exit
        )
        self.process_manager.start()

    def on_process_output(self, data):
        # Schedule update on UI thread
        self.call_from_thread(self._handle_output, data)

    def _handle_output(self, data):
        term = self.query_one(TerminalWidget)
        term.write(data)

        # Parse for events
        events = self.parser.parse(data)
        for event in events:
            self.query_one("#metrics_log").write(f"[{event.type}] {event.content}")

    def on_process_exit(self, code):
        self.exit(code)

    def action_quit(self):
        if self.process_manager:
            self.process_manager.stop()
        super().action_quit()
