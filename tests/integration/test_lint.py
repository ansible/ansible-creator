"""Check scaffolded content integration with ansible-lint."""

import re
import shlex
import subprocess

from pathlib import Path

import pytest


@pytest.fixture()
def collection_path(tmp_path: Path) -> Path:
    """Create a temporary directory for the collection.

    Args:
        tmp_path: Temporary path.
    """
    test_path = ("collections", "ansible_collections")
    final_dest = tmp_path.joinpath(*test_path)
    final_dest.mkdir(parents=True, exist_ok=True)
    return final_dest


def test_create_collection(collection_path: Path) -> None:
    """Scaffold a collection with ansible-creator.

    Args:
        collection_path: Path for scaffolded collection.
    """
    # Check that the collection path is present.
    assert collection_path.exists

    # Define args for ansible-creator
    creator_args = [
        "ansible-creator",
        "init",
        "testorg.testcol",
        "--init-path",
        str(collection_path),
    ]

    # Join the args into a command
    creator_command = shlex.join(creator_args)

    # Create a test collection in the testorg namespace.
    result = subprocess.run(
        creator_command,
        text=True,
        shell=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0

    # Check stdout for the collection creation message.
    assert re.search("Note: collection testorg.testcol created at", result.stdout) is not None


def test_lint_collection(collection_path: Path) -> None:
    """Lint the scaffolded collection with ansible-lint."""
    # Check that the scaffolded collection exists.
    collection_dir = collection_path / "testorg" / "testcol"
    assert collection_dir.exists

    # Validate the collection with ansible-lint.
    result = subprocess.run(
        ["ansible-lint", collection_dir],
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        print("Standard Output:", result.stdout)
        print("Standard Error:", result.stderr)

    assert result.returncode == 0

    # Check stdout for the linting success message.
    assert (
        re.search(
            r"Passed: 0 failures, 0 warnings on \d+ files.*",
            result.stdout,
        )
        is not None
    )
