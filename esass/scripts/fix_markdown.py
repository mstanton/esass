import re
import sys
import subprocess
import os
from pathlib import Path


def get_node_bin_path():
    """Try to find the node/npx binary path from NVM or shell."""
    # Try where command first
    try:
        result = subprocess.run(
            ["where", "npx"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            return os.path.dirname(result.stdout.splitlines()[0])
    except:
        pass

    # Try NVM for Windows standard paths
    nvm_root = os.environ.get("NVM_HOME") or os.path.expandvars(r"%APPDATA%\Local\nvm")
    if os.path.exists(nvm_root):
        # Look for active version
        symlink_path = r"C:\Program Files\nodejs"
        if os.path.exists(symlink_path):
            return symlink_path

        # Try to find any version directory
        versions = [
            d for d in Path(nvm_root).iterdir() if d.is_dir() and d.name.startswith("v")
        ]
        if versions:
            # Sort by version number (naive)
            versions.sort(reverse=True)
            return str(versions[0])

    return None


def run_standard_linter(file_path):
    """Try to run a standard linter using discovered node bin path."""
    bin_path = get_node_bin_path()
    env = os.environ.copy()
    if bin_path:
        print(f"Adding {bin_path} to PATH for this run.")
        env["PATH"] = bin_path + os.pathsep + env.get("PATH", "")

        npx_path = "npx"
        if bin_path:
            cmd_path = os.path.join(bin_path, "npx.cmd")
            if os.path.exists(cmd_path):
                npx_path = cmd_path

    try:
        print(f"Attempting to run markdownlint-cli2 on {file_path}...")
        # Use -y to avoid confirmation prompts for npx
        result = subprocess.run(
            [npx_path, "-y", "markdownlint-cli2", "--fix", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
            env=env,
            shell=True,  # Required for finding .cmd on Windows
        )
        if result.returncode == 0:
            print("Standard linter fixed the file.")
            return True
        else:
            print("Standard linter could not fix all issues or encountered an error.")
            print(result.stdout)
            print(result.stderr)
    except Exception as e:
        print(f"Error running standard linter: {e}")
    return False


def fix_markdown_custom(file_path):
    # (Same custom logic as before as a safety fallback)
    path = Path(file_path)
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    fixed_lines = []
    inside_block = False
    for i, line in enumerate(lines):
        if i == 0 and not inside_block:
            if line.startswith("## "):
                line = "# " + line[3:]
        if line.strip().startswith("```"):
            if not inside_block:
                inside_block = True
                if not line.strip()[3:].strip():
                    line = f"{line.strip()}text"
            else:
                inside_block = False
        fixed_lines.append(line)
    path.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")
    print(f"Custom fixes applied to {file_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if not run_standard_linter(target):
            fix_markdown_custom(target)
    else:
        print("Usage: python fix_markdown.py <file_path>")
