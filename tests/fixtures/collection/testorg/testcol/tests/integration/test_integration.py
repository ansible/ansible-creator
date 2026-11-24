"""Tests for molecule scenarios."""

from __future__ import absolute_import, division, print_function

import subprocess

from pathlib import Path


def test_integration() -> None:
    """Run molecule test --all for each scenario."""
    extensions_dir = Path(__file__).resolve().parents[2] / "extensions"

    proc = subprocess.run(
        ["molecule", "test", "--all"],
        cwd=extensions_dir,
    )
    assert proc.returncode == 0
