"""Check fixture content integration with ansible-lint.

The fixture content is compared to the output of ansible-creator in the
test_run_success_for_collection and test_run_success_ansible_project
tests.
"""

from __future__ import annotations

import re
import sys

from pathlib import Path
from typing import TYPE_CHECKING

from tests.defaults import FIXTURES_DIR


if TYPE_CHECKING:
    import pytest

    from tests.conftest import CliRunCallable

GALAXY_BIN = Path(sys.executable).parent / "ansible-galaxy"
LINT_BIN = Path(sys.executable).parent / "ansible-lint"

LINT_RE = re.compile(
    r"Passed: (?P<failures>\d+) failure\(s\),"
    r" (?P<warnings>\d+) warning\(s\) on (?P<files>\d+) files.",
)
LINT_PROFILE_RE = re.compile(
    r"Last profile that met the validation criteria was '(?P<profile>\w+)'.",
)


def test_lint_collection(
    cli: CliRunCallable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lint the scaffolded collection with ansible-lint.

    Args:
        cli: CLI callable.
        monkeypatch: Monkeypatch fixture.
    """
    project_path = FIXTURES_DIR / "collection"
    monkeypatch.chdir(project_path)

    args = str(LINT_BIN)
    env = {"NO_COLOR": "1"}
    result = cli(args=args, env=env)

    assert result.returncode == 0

    match = LINT_RE.search(result.stderr)
    assert match is not None
    assert int(match.group("failures")) == 0
    assert int(match.group("warnings")) == 0
    assert int(match.group("files")) > 0

    match = LINT_PROFILE_RE.search(result.stderr)
    assert match is not None
    assert match.group("profile") == "production"


def test_lint_playbook_project(
    tmp_path: Path,
    cli: CliRunCallable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lint the scaffolded playbook project with ansible-lint.

    This is an expensive test as it installs collections from the requirements.yml file.
    If it becomes necessary again, consider using a session fixture to install the collections.

    Args:
        tmp_path: Temporary path.
        cli: CLI callable.
        monkeypatch: Monkeypatch fixture.
    """
    req_path = str(
        FIXTURES_DIR / "project" / "playbook_project" / "collections" / "requirements.yml",
    )
    dest_path = tmp_path / "collections"
    galaxy_cmd = f"{GALAXY_BIN} collection install -r {req_path} -p {dest_path}"
    result = cli(args=galaxy_cmd)
    assert result.returncode == 0

    project_path = FIXTURES_DIR / "project" / "playbook_project"
    monkeypatch.chdir(project_path)
    args = str(LINT_BIN)
    env = {"NO_COLOR": "1", "ANSIBLE_COLLECTIONS_PATH": str(dest_path)}
    result = cli(args=args, env=env)

    assert result.returncode == 0

    match = LINT_RE.search(result.stderr)
    assert match is not None
    assert int(match.group("failures")) == 0
    assert int(match.group("warnings")) == 0
    assert int(match.group("files")) > 0

    match = LINT_PROFILE_RE.search(result.stderr)
    assert match is not None
    assert match.group("profile") == "production"
