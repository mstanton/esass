"""
Shared fixtures for openclaw-plugin tests.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

# Ensure project root is on sys.path so imports work
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Alias the plugin package so `openclaw_plugin` can be imported
_plugin_root = str(Path(__file__).resolve().parents[1])
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

# Make `import openclaw_plugin` resolve to the plugin package
import importlib
if "openclaw_plugin" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "openclaw_plugin",
        os.path.join(_plugin_root, "__init__.py"),
        submodule_search_locations=[_plugin_root],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["openclaw_plugin"] = mod
    spec.loader.exec_module(mod)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory tree for tracing stores."""
    usage_dir = tmp_path / "tracing" / "usage"
    evo_dir = tmp_path / "tracing" / "evolution"
    lineage_dir = tmp_path / "tracing" / "lineage"
    usage_dir.mkdir(parents=True)
    evo_dir.mkdir(parents=True)
    lineage_dir.mkdir(parents=True)
    return {
        "root": tmp_path,
        "usage": str(usage_dir),
        "evolution": str(evo_dir),
        "lineage": str(lineage_dir),
    }


@pytest.fixture
def tmp_skills_dir(tmp_path):
    """Provide a temporary skills output directory."""
    d = tmp_path / "skills" / "generated"
    d.mkdir(parents=True)
    return str(d)
