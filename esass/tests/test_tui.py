import pytest
from esass_prototype.tui.app import ESASSApp
from esass_prototype.tui.parser import StreamParser


@pytest.mark.asyncio
async def test_app_startup():
    app = ESASSApp(command=["python", "--version"])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.process_manager is not None
        # Check if terminal widget is present
        assert app.query_one("TerminalWidget")


def test_parser():
    parser = StreamParser()
    events = parser.parse("Tool Call: read_file(path='test.py')")
    assert len(events) == 1
    assert events[0].type == "tool_call_start"

    # Correct format
    events = parser.parse("Tool Call: Read")
    assert len(events) == 1
    assert events[0].type == "tool_call_start"
    assert events[0].content == "Read"

    events = parser.parse("Thinking: I should do this.")
    assert len(events) == 1
    assert events[0].type == "thinking"
