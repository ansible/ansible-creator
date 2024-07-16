"""Test the output module."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ansible_creator.output import console_width


@pytest.mark.parametrize(argnames="width, expected", argvalues=((79, 79), (131, 81), (133, 132)))
def test_console_width(width: int, expected: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the console width function."""

    def mock_get_terminal_size() -> SimpleNamespace:
        return SimpleNamespace(columns=width, lines=24)

    monkeypatch.setattr("shutil.get_terminal_size", mock_get_terminal_size)

    monkeypatch.delenv("COLUMNS", raising=False)

    assert console_width() == expected
