"""
`esass init` command - sets up ESASS in the current project.

Creates config, data dirs, hooks, and Claude Code integration files.
"""

import json
import os
import sys
from pathlib import Path

import click
import yaml


HOOKS_CONFIG = {
    "PostToolUse": [
        {
            "command": "python -m esass.hooks.post_tool_use",
            "timeout": 5000,
        }
    ],
    "SessionStart": [
        {
            "command": "python -m esass.hooks.session_start",
            "timeout": 10000,
        }
    ],
}

DEFAULT_CONFIG = {
    "observation": {"enabled": True, "mode": "live"},
    "storage": {"log_format": "jsonl", "max_log_age_days": 90},
    "pattern_detection": {
        "min_support": 10,
        "min_confidence": 0.8,
        "min_stability_days": 7,
    },
    "probes": {"enabled": True, "buffer_size": 100, "flush_interval": 5.0},
    "semantic_extraction": {
        "noise_tags": [
            "boundary_action",
            "hook_error",
            "hook_success",
            "unknown",
            "none",
            "null",
            "",
        ]
    },
}

ESASS_COMMAND_MD = """\
# ESASS Commands

Run ESASS operations from Claude Code.

## Usage

$ARGUMENTS
Subcommand to run (e.g., status, analyze, tail 20, monitor)

## Available Commands

- `status` / `stats` - Show ESASS statistics
- `analyze` - Detect patterns in observation logs
- `generate-skills` - Generate skills from patterns
- `tail [N]` - Show last N events (default: 20)
- `monitor` - Realtime event monitoring
- `pipeline` - Run full observe->analyze->generate->export pipeline
- `export` - Export to Obsidian vault
- `init` - Re-run project setup
"""


def _echo_step(msg: str, ok: bool = True):
    prefix = click.style("  +", fg="green") if ok else click.style("  ~", fg="yellow")
    click.echo(f"{prefix} {msg}")


def _detect_environment(project_dir: Path) -> dict:
    """Detect what's available in the current project."""
    env = {
        "has_claude": (project_dir / ".claude").is_dir(),
        "has_git": (project_dir / ".git").is_dir(),
        "has_esass": (project_dir / ".esass").is_dir(),
        "has_mcp_json": (project_dir / ".mcp.json").is_file(),
    }
    return env


def _run_preflight_checks(enable_mcp: bool = False) -> bool:
    """Check for basic requirements before init."""
    click.echo("  Running pre-flight checks...")
    all_ok = True

    # Python Version
    py_ver = sys.version_info
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 10):
        _echo_step(
            f"Python 3.10+ required (found {py_ver.major}.{py_ver.minor})", ok=False
        )
        all_ok = False
    else:
        _echo_step("Python version OK")

    # Ollama (if MCP enabled)
    if enable_mcp:
        try:
            import httpx

            # Quick check if Ollama is running
            response = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
            if response.status_code == 200:
                _echo_step("Ollama service detected")
            else:
                _echo_step("Ollama service not responding", ok=False)
                # Don't fail init, just warn
        except Exception:
            _echo_step("Ollama service not detected (required for MCP)", ok=False)

    return all_ok


def _create_config(esass_dir: Path, project_dir: Path):
    """Create .esass/config.yaml from defaults."""
    config_file = esass_dir / "config.yaml"
    if config_file.exists():
        _echo_step("Config already exists, skipping", ok=False)
        return

    config = dict(DEFAULT_CONFIG)
    config["storage"]["data_dir"] = str(esass_dir / "data")

    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    _echo_step(f"Created {config_file.relative_to(project_dir)}")


def _create_data_dir(esass_dir: Path, project_dir: Path):
    """Create .esass/data/ directory structure."""
    data_dir = esass_dir / "data"
    for subdir in ["logs", "state", "patterns", "skills"]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)

    _echo_step(f"Created {data_dir.relative_to(project_dir)}/")


def _update_gitignore(project_dir: Path):
    """Add .esass/data/ to .gitignore if not already present."""
    gitignore = project_dir / ".gitignore"
    entry = ".esass/data/"

    if gitignore.exists():
        content = gitignore.read_text()
        if entry in content:
            _echo_step(".gitignore already has .esass/data/", ok=False)
            return
        # Append
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n# ESASS data (local, not committed)\n{entry}\n"
        gitignore.write_text(content)
    else:
        gitignore.write_text(f"# ESASS data (local, not committed)\n{entry}\n")

    _echo_step("Added .esass/data/ to .gitignore")


def _install_hooks(global_install: bool = False):
    """Install hooks to ~/.claude/hooks.json (merge, don't overwrite)."""
    hooks_file = Path.home() / ".claude" / "hooks.json"

    if hooks_file.exists():
        try:
            existing = json.loads(hooks_file.read_text())
        except (json.JSONDecodeError, ValueError):
            existing = {}
    else:
        existing = {}

    hooks = existing.get("hooks", {})

    # Merge each hook type
    for hook_type, hook_entries in HOOKS_CONFIG.items():
        existing_entries = hooks.get(hook_type, [])

        # Check if esass hooks already installed (by command substring)
        esass_commands = {e["command"] for e in hook_entries}
        existing_commands = {e.get("command", "") for e in existing_entries}

        for entry in hook_entries:
            if entry["command"] not in existing_commands:
                existing_entries.append(entry)

        hooks[hook_type] = existing_entries

    existing["hooks"] = hooks

    hooks_file.parent.mkdir(parents=True, exist_ok=True)
    hooks_file.write_text(json.dumps(existing, indent=2) + "\n")

    _echo_step(f"Installed hooks to {hooks_file}")


def _create_claude_command(project_dir: Path):
    """Create .claude/commands/esass.md for the /esass slash command."""
    commands_dir = project_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    cmd_file = commands_dir / "esass.md"
    if cmd_file.exists():
        _echo_step("Claude command already exists, skipping", ok=False)
        return

    cmd_file.write_text(ESASS_COMMAND_MD)
    _echo_step(f"Created {cmd_file.relative_to(project_dir)}")


def _configure_path():
    """Ensure the Python scripts directory is on the user's PATH."""
    if sys.platform == "win32":
        scripts_dir = Path(sys.executable).parent / "Scripts"
    else:
        scripts_dir = Path(sys.executable).parent

    scripts_str = str(scripts_dir)

    # Check if already on PATH (case-insensitive on Windows)
    current_path = os.environ.get("PATH", "")
    if sys.platform == "win32":
        path_entries = [p.lower() for p in current_path.split(";")]
        already_on_path = scripts_str.lower() in path_entries
    else:
        path_entries = current_path.split(":")
        already_on_path = scripts_str in path_entries

    if already_on_path:
        _echo_step("Scripts directory already on PATH", ok=False)
        return

    if sys.platform == "win32":
        _configure_path_windows(scripts_str)
    else:
        _configure_path_unix(scripts_str)


def _configure_path_windows(scripts_dir: str):
    """Add scripts_dir to the user PATH via the Windows registry."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS
        )
        try:
            user_path, _ = winreg.QueryValueEx(key, "PATH")
        except FileNotFoundError:
            user_path = ""

        # Check again against the registry value (may differ from env)
        entries = [p.lower() for p in user_path.split(";") if p]
        if scripts_dir.lower() in entries:
            _echo_step("Scripts directory already on user PATH", ok=False)
            winreg.CloseKey(key)
            return

        new_path = f"{user_path};{scripts_dir}" if user_path else scripts_dir
        winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)

        _echo_step(f"Added {scripts_dir} to user PATH (restart terminal to apply)")
    except OSError as exc:
        _echo_step(f"Could not update PATH: {exc}", ok=False)


def _configure_path_unix(scripts_dir: str):
    """Append an export line to the user's shell profile."""
    shell = os.environ.get("SHELL", "")
    export_line = f'export PATH="$PATH:{scripts_dir}"  # Added by esass init'

    if shell.endswith("zsh"):
        profile = Path.home() / ".zshrc"
    elif shell.endswith("fish"):
        profile = Path.home() / ".config" / "fish" / "config.fish"
        export_line = f"set -gx PATH $PATH {scripts_dir}  # Added by esass init"
    else:
        # Default to bash
        bashrc = Path.home() / ".bashrc"
        profile = bashrc if bashrc.exists() else Path.home() / ".bash_profile"

    # Don't duplicate if already present
    if profile.exists():
        content = profile.read_text()
        if scripts_dir in content:
            _echo_step(f"Scripts directory already in {profile.name}", ok=False)
            return
    else:
        content = ""

    if not content.endswith("\n") and content:
        content += "\n"
    content += f"\n{export_line}\n"

    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(content)
    _echo_step(f"Added {scripts_dir} to {profile.name} (restart terminal to apply)")


def _configure_mcp(project_dir: Path, ollama_model: str = "gemma4:31b"):
    """Add esass-mcp-server to .mcp.json with env vars from global config."""
    from esass.config import load_global_mcp_env

    mcp_file = project_dir / ".mcp.json"

    if mcp_file.exists():
        try:
            existing = json.loads(mcp_file.read_text())
        except (json.JSONDecodeError, ValueError):
            existing = {}
    else:
        existing = {}

    servers = existing.get("mcpServers", {})

    if "local-llm-mcp" in servers:
        _echo_step("MCP server already configured, skipping", ok=False)
        return

    # Build env from global config, with explicit model override
    env = load_global_mcp_env()
    env["OLLAMA_MODEL"] = ollama_model

    servers["local-llm-mcp"] = {
        "command": "python -m esass.mcp.server",
        "env": env,
    }

    existing["mcpServers"] = servers
    mcp_file.write_text(json.dumps(existing, indent=2) + "\n")

    _echo_step("Added esass-mcp-server to .mcp.json")


def _create_claude_settings(project_dir: Path):
    """Create .claude/settings.local.json with MCP permissions pre-approved."""
    settings_dir = project_dir / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)

    settings_file = settings_dir / "settings.local.json"

    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text())
        except (json.JSONDecodeError, ValueError):
            existing = {}
    else:
        existing = {}

    # Ensure MCP tools are in the allow list
    permissions = existing.get("permissions", {})
    allow = set(permissions.get("allow", []))

    mcp_tools = [
        "mcp__local-llm-mcp__execute_skill",
        "mcp__local-llm-mcp__analyze_pattern",
        "mcp__local-llm-mcp__generate_skill_name",
        "mcp__local-llm-mcp__check_availability",
        "mcp__local-llm-mcp__get_routing_stats",
        "mcp__local-llm-mcp__get_cost_dashboard",
        "mcp__local-llm-mcp__get_full_analytics",
        "mcp__local-llm-mcp__get_adaptive_status",
    ]
    allow.update(mcp_tools)

    permissions["allow"] = sorted(allow)
    existing["permissions"] = permissions

    settings_file.write_text(json.dumps(existing, indent=2) + "\n")
    _echo_step("Created .claude/settings.local.json with MCP permissions")


def _quick_init(project_dir: Path, ollama_model: str):
    """Fast bootstrap: .mcp.json + .claude/settings.local.json + data dirs only."""
    from esass.config import ensure_global_config

    # Ensure global config exists
    ensure_global_config()

    # Create data dirs
    esass_dir = project_dir / ".esass"
    data_dir = esass_dir / "data"
    for subdir in ["logs", "state", "patterns", "skills"]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Create .mcp.json with MCP server
    _configure_mcp(project_dir, ollama_model)

    # Create .claude/settings.local.json with permissions
    _create_claude_settings(project_dir)

    # Ensure scripts directory is on PATH
    _configure_path()

    click.echo(
        click.style("  ESASS ready!", fg="green", bold=True) + f" ({project_dir.name})"
    )


@click.command("init")
@click.option(
    "--global",
    "global_install",
    is_flag=True,
    help="Install hooks and data in ~/",
)
@click.option("--enable-mcp", is_flag=True, help="Configure MCP server")
@click.option(
    "--ollama-model", default="gemma4:31b", help="Ollama model for MCP server"
)
@click.option("--yes", "-y", is_flag=True, help="Non-interactive mode")
@click.option(
    "--quick",
    "-q",
    is_flag=True,
    help="Fast bootstrap: .mcp.json + permissions + data dirs",
)
def init(global_install, enable_mcp, ollama_model, yes, quick):
    """Initialize ESASS in the current project."""
    project_dir = Path.cwd()

    if quick:
        _quick_init(project_dir, ollama_model)
        return

    click.echo()
    click.echo(click.style("  ESASS Init", bold=True))
    click.echo()

    # 0. Pre-flight checks
    if not _run_preflight_checks(enable_mcp):
        if not yes and not click.confirm(
            "  Requirements not fully met. Proceed anyway?", default=False
        ):
            click.echo("  Aborted.")
            return

    # Detect environment
    click.echo("  Detecting environment...")
    env = _detect_environment(project_dir)

    if env["has_claude"]:
        _echo_step("Claude Code project (.claude/ found)")
    else:
        _echo_step("No .claude/ directory (will create)", ok=False)

    if env["has_git"]:
        _echo_step("Git repository")
    else:
        _echo_step("Not a git repository", ok=False)

    if env["has_esass"]:
        _echo_step("Existing .esass/ found (will merge)", ok=False)

    click.echo()

    if not yes:
        if not click.confirm("  Proceed with setup?", default=True):
            click.echo("  Aborted.")
            return

    click.echo()

    # 1. Create .esass/ directory and config
    esass_dir = project_dir / ".esass"
    esass_dir.mkdir(exist_ok=True)
    _create_config(esass_dir, project_dir)

    # 2. Create data directory
    _create_data_dir(esass_dir, project_dir)

    # 3. Update .gitignore
    if env["has_git"]:
        _update_gitignore(project_dir)

    # 4. Install hooks
    _install_hooks(global_install)

    # 5. Create Claude Code command
    _create_claude_command(project_dir)

    # 6. Ensure scripts directory is on PATH
    _configure_path()

    # 7. Optionally configure MCP
    if enable_mcp:
        _configure_mcp(project_dir, ollama_model)

    click.echo()
    click.echo(click.style("  Setup Summary:", bold=True))
    _echo_step(f"Project: {project_dir.name}")
    _echo_step("Config: .esass/config.yaml")
    _echo_step("Hooks: ~/.claude/hooks.json")
    if enable_mcp:
        _echo_step(f"MCP: .mcp.json ({ollama_model})")

    click.echo()
    click.echo(
        click.style("  ESASS ready!", fg="green", bold=True)
        + " Restart Claude Code to activate hooks."
    )
    click.echo()
