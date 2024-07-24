"""Check scaffolded content integration with ansible-lint."""

import re
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def collection_path(tmp_path: Path) -> Path:
    """Create a temporary directory for the collection.

    Args:
        tmp_path: Temporary path.

    Returns:
        Path: Temporary directory for the collection.
    """
    test_path = ("collections", "ansible_collections")
    final_dest = tmp_path.joinpath(*test_path)
    final_dest.mkdir(parents=True, exist_ok=True)
    return final_dest


@pytest.fixture()
def scaffold_collection(collection_path: Path) -> Path:
    """Scaffold a collection with ansible-creator.

    Args:
        collection_path: Path for scaffolded collection.

    Returns:
        Path: Path for scaffolded collection.
    """
    assert collection_path.exists

    creator_command = [
        sys.executable,
        "-Im",
        "ansible_creator",
        "init",
        "testorg.testcol",
        "--init-path",
        str(collection_path),
    ]

    result = subprocess.check_output(creator_command, text=True)

    assert re.search("Note: collection testorg.testcol created at", result) is not None

    return collection_path


def remove_ansi_escape_codes(text: str) -> str:
    """Clean up ansi escape codes from stdout and stderr.

    Args:
        text: The input text string.

    Returns:
        str: The text string without ansi escape codes.
    """
    ansi_escape = re.compile(r"(?:\x1B[@-_][0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def test_lint_collection(scaffold_collection: Path) -> None:
    """Lint the scaffolded collection with ansible-lint.

    Args:
        scaffold_collection: Path for scaffolded collection.
    """
    assert scaffold_collection.exists

    result = subprocess.run(
        ["ansible-lint", scaffold_collection],
        text=True,
        capture_output=True,
        check=False,
    )

    clean_stdout = remove_ansi_escape_codes(result.stdout)
    clean_stderr = remove_ansi_escape_codes(result.stderr)

    assert result.returncode == 0

    assert (
        re.search(
            r"Passed: 0 failure\(s\), 0 warning\(s\) on \d+ files.",
            clean_stdout + clean_stderr,
        )
        is not None
    )
