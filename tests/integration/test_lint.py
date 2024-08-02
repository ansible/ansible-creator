"""Check scaffolded content integration with ansible-lint."""

import re
import subprocess
import sys

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _disable_ansi_cli_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")


@pytest.fixture(name="collection_path")
def create_collection_path(tmp_path: Path) -> Path:
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


@pytest.fixture(name="scaffold_collection")
def create_scaffolded_collection(collection_path: Path) -> Path:
    """Scaffold a collection with ansible-creator.

    Args:
        collection_path: Path for scaffolded collection.

    Returns:
        Path: Path for scaffolded collection.
    """
    creator_command = [
        sys.executable,
        "-Im",
        "ansible_creator",
        "init",
        "testorg.testcol",
        "--init-path",
        str(collection_path),
    ]

    result = subprocess.check_output(
        creator_command,
        text=True,
    )

    assert re.search("Note: collection testorg.testcol created at", result) is not None

    return collection_path


def test_lint_collection(scaffold_collection: Path) -> None:
    """Lint the scaffolded collection with ansible-lint.

    Args:
        scaffold_collection: Path for scaffolded collection.
    """
    assert (
        scaffold_collection.exists()
    ), f"Expected to find the {scaffold_collection} directory but it does not exist."

    lint_command = [
        sys.executable,
        "-Im",
        "ansiblelint",
        str(scaffold_collection),
    ]

    result = subprocess.run(
        lint_command,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0

    assert (
        re.search(
            r".*Passed: 0 failure\(s\), 0 warning\(s\) on \d+ files\..*",
            result.stderr,
            re.DOTALL,
        )
        is not None
    )
