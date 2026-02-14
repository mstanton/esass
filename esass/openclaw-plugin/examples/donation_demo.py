#!/usr/bin/env python3
"""
Donation display demo.

Shows PayPal link in all three formats: agent, human, and markdown badge.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)
_plugin = str(Path(__file__).resolve().parents[1])
if _plugin not in sys.path:
    sys.path.insert(0, _plugin)

import importlib, os
if "openclaw_plugin" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "openclaw_plugin",
        os.path.join(_plugin, "__init__.py"),
        submodule_search_locations=[_plugin],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["openclaw_plugin"] = mod
    spec.loader.exec_module(mod)

from openclaw_plugin.donation.models import DonationConfig
from openclaw_plugin.donation.display import DonationDisplay


def main():
    config = DonationConfig()
    display = DonationDisplay(config=config)

    skill = "git-commit-helper"

    print("=" * 60)
    print("ESASS Donation Display Demo")
    print("=" * 60)

    # 1. Agent format
    print("\n--- Agent Format (structured dict) ---")
    agent_data = display.render_for_agent(skill)
    for k, v in agent_data.items():
        print(f"  {k}: {v}")

    # 2. Human format
    print("\n--- Human Format (CLI output) ---")
    print(display.render_for_human(skill))

    # 3. Markdown badge
    print("\n--- Markdown Badge ---")
    print(display.render_markdown_badge())

    # 4. Activation message (log line)
    print("\n--- Activation Log Line ---")
    print(display.render_activation_message(skill))

    print("\n" + "=" * 60)
    print("Donation demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
