"""Constants with default values used throughout the tests."""

from __future__ import annotations

import sys

from pathlib import Path


FIXTURES_DIR = (Path(__file__).parent / "fixtures").resolve()
CREATOR_BIN = Path(sys.executable).parent / "ansible-creator"

UUID_LENGTH = 8
