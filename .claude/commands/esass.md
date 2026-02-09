---
description: Run ESASS (Emergent Self-Adaptive Skill System) commands - manage observation, analysis, skill generation, and monitoring
allowed-tools: Bash(python:*), Bash(uv run:*), Bash(cd:*), Bash(powershell.exe:*)
---

## ESASS Command Hub

ESASS is a meta-cognitive architecture that enables AI skills to achieve operational self-awareness through observation, pattern recognition, and autonomous skill formation.

## Available Subcommands

Based on arguments provided by the user, execute the appropriate ESASS command:

### Quick Reference

| Command | Description |
|---------|-------------|
| `/esass` (no args) | Show status dashboard |
| `/esass status` | Display system statistics and probe health |
| `/esass watch` | Launch realtime event monitor |
| `/esass dashboard` | Launch ESASS Unified Dashboard in external terminal |
| `/esass analyze` | Detect patterns from observation logs |
| `/esass generate` | Generate skills from validated patterns |
| `/esass pipeline` | Run full observe->analyze->generate->export pipeline |
| `/esass export` | Export patterns and skills to Obsidian vault |
| `/esass setup` | Show setup instructions |

## Execution

### Default (no arguments) - Show Status

If no arguments provided, display current ESASS status:

```bash
cd "C:\workspace\ESASS\esass" && python -c "
import subprocess
import sys

# Run status check
result = subprocess.run([sys.executable, 'esass/hooks/esass_notify.py', 'inline'], capture_output=True, text=True)
if result.stdout:
    print(result.stdout)
if result.stderr:
    print(result.stderr)
"
```

### status - System Statistics

```bash
cd "C:\workspace\ESASS\esass" && uv run esass stats
```

### watch - Realtime Monitor

```bash
cd "C:\workspace\ESASS\esass" && uv run esass watch
```

### dashboard - Launch External Dashboard

Launch the ESASS Unified Dashboard in a new PowerShell window:

```bash
powershell.exe -NoProfile -Command "Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', 'C:\workspace\ESASS\esass\esass\hooks\esass_dashboard.ps1'"
```

### analyze - Pattern Detection

```bash
cd "C:\workspace\ESASS\esass" && uv run esass analyze --days 7
```

### generate - Skill Generation

```bash
cd "C:\workspace\ESASS\esass" && uv run esass generate-skills
```

### pipeline - Full Pipeline

```bash
cd "C:\workspace\ESASS\esass" && uv run esass pipeline
```

### export - Obsidian Export

```bash
cd "C:\workspace\ESASS\esass" && uv run esass export
```

### setup - Show Setup Instructions

```bash
cd "C:\workspace\ESASS\esass" && uv run esass setup
```

### audit - Launch Skill Auditor TUI

```bash
cd "C:\workspace\ESASS\esass" && uv run esass audit
```

## Your Task

1. Parse the user's arguments to determine which subcommand to run
2. Execute the appropriate bash command from above
3. Display the results clearly

If the user provides an unrecognized subcommand, show the quick reference table.
