"""Unit tests for ansible-creator docs."""

from __future__ import annotations

import re
import sys
from textwrap import dedent


def test_run_docs_no_input(cli):
    result = cli("ansible-creator docs")
    assert result.returncode != 0
    assert "Error: unable to find galaxy.yml in ." in result.stderr
