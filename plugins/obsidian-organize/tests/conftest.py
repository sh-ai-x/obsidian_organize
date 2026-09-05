"""Pytest configuration + shared fixtures."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# Make the plugin's _lib importable without installation.
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PLUGIN_ROOT / "skills"
if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

FIXTURE_VAULT = PLUGIN_ROOT / "tests" / "fixtures" / "vault"


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Copy the fixture vault into tmp_path and return the new root.

    Each test gets its own isolated vault; mutations never bleed across
    tests, and the real vault at tests/fixtures/vault stays pristine.
    """
    if not FIXTURE_VAULT.exists():
        # First-run: bootstrap an empty vault.
        (tmp_path / "_research").mkdir(parents=True)
        (tmp_path / "topics").mkdir(parents=True)
        (tmp_path / "sources").mkdir(parents=True)
        return tmp_path
    dest = tmp_path / "vault"
    shutil.copytree(FIXTURE_VAULT, dest)
    return dest


@pytest.fixture
def fixed_now():
    """A deterministic datetime for tests."""
    from datetime import datetime, timezone

    return datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
