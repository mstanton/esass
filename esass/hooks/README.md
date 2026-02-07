# ESASS Hooks - Claude Code Integration

Simple CLI-based pattern analyzer and realtime monitoring for Claude Code.

## Quick Start

### 1. Test the Setup

```bash
python esass_cli.py test
```

This simulates tool calls and verifies everything is working.

### 2. Configure Claude Code Hook

Add to `~/.claude/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "command": "python C:/workspace/ESASS/esass/esass/hooks/esass_hook.py",
      "timeout": 5000
    }]
  }
}
```

### 3. Start Monitoring

In a separate terminal:

```bash
python esass_cli.py watch
```

### 4. Use Claude Code

All tool usage will be automatically captured.

## CLI Commands

| Command | Description |
|---------|-------------|
| `watch` | Realtime monitoring of tool usage |
| `stats` | Show session statistics |
| `patterns` | Analyze detected patterns |
| `skills` | View/generate skill candidates |
| `tail [N]` | Show last N events |
| `setup` | Show setup instructions |
| `test` | Test the ESASS setup |
| `clear` | Clear all ESASS data |

## Examples

```bash
# Watch tool usage in realtime
python esass_cli.py watch

# View statistics for the last 7 days
python esass_cli.py stats

# Analyze patterns
python esass_cli.py patterns

# Generate skill candidates and save them
python esass_cli.py skills --save

# View last 50 events
python esass_cli.py tail 50
```

## Data Storage

Data is stored in `~/.esass/data/`:

```
~/.esass/data/
├── logs/           # Daily event logs (JSONL)
├── state/          # Sequence tracking state
├── patterns/       # Detected patterns
└── skills/         # Generated skill candidates
```

Set `ESASS_DATA_DIR` environment variable to use a different location.

## Files

- `esass_hook.py` - Hook script that captures Claude Code tool calls
- `esass_cli.py` - Main CLI tool for monitoring and analysis
