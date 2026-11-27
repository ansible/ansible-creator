"""Tests for molecule scenarios."""

from __future__ import absolute_import, division, print_function

import subprocess
import sys

from pathlib import Path


def test_integration() -> None:
    """Run molecule for each scenario.

    Invokes the Molecule CLI directly. ``molecule test --all`` discovers
    scenarios from ``extensions/molecule`` and skips shared content that has
    no ``molecule.yml``.
    """
    collection_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "molecule", "test", "--all"],
        check=False,
        cwd=collection_root,
    )
    assert proc.returncode == 0
