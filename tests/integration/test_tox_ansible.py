"""Integration tests that run tox-ansible on scaffolded collections.

Scaffolds a collection with ansible-creator, then runs tox-ansible sanity
and galaxy checks against it to ensure the generated content stays valid.
"""

from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.defaults import CREATOR_BIN


if TYPE_CHECKING:
    from tests.conftest import CliRunCallable

TOX_BIN = Path(sys.executable).parent / "tox"


@pytest.fixture
def _scaffolded_collection(
    cli: CliRunCallable,
    tmp_path: Path,
) -> Path:
    """Scaffold a fresh collection into a temporary directory.

    Args:
        cli: CLI callable.
        tmp_path: Temporary path.

    Returns:
        Path to the scaffolded collection.
    """
    dest = tmp_path / "scaffolded"
    result = cli(f"{CREATOR_BIN} init collection testns.testcol {dest}")
    assert result.returncode == 0, f"Scaffold failed: {result.stderr}"
    return dest


@pytest.mark.slow
def test_tox_ansible_sanity(
    _scaffolded_collection: Path,
    cli: CliRunCallable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run tox-ansible sanity checks on a scaffolded collection.

    Args:
        _scaffolded_collection: Path to the scaffolded collection.
        cli: CLI callable.
        monkeypatch: Monkeypatch fixture.
    """
    monkeypatch.chdir(_scaffolded_collection)

    result = cli(
        f"{TOX_BIN} l --ansible -c tox-ansible.ini",
        env={"NO_COLOR": "1"},
    )
    assert result.returncode == 0, f"tox list failed: {result.stderr}"

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    sanity_envs = [
        line.split()[0]
        for line in (result.stdout or "").splitlines()
        if line.strip().startswith(f"sanity-py{py_version}-")
    ]
    if not sanity_envs:
        pytest.skip(f"No sanity envs available for py{py_version}")

    sanity_env = sanity_envs[0]
    result = cli(
        f"{TOX_BIN} --ansible -c tox-ansible.ini -e {sanity_env}",
        env={"NO_COLOR": "1"},
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, f"tox-ansible sanity failed:\n{combined}"
    assert "congratulations" in combined.lower()


@pytest.mark.slow
def test_tox_ansible_galaxy(
    _scaffolded_collection: Path,
    cli: CliRunCallable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run tox-ansible galaxy-importer on a scaffolded collection.

    Args:
        _scaffolded_collection: Path to the scaffolded collection.
        cli: CLI callable.
        monkeypatch: Monkeypatch fixture.
    """
    monkeypatch.chdir(_scaffolded_collection)

    result = cli(
        f"{TOX_BIN} --ansible -c tox-ansible.ini -e galaxy",
        env={"NO_COLOR": "1"},
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, f"tox-ansible galaxy failed:\n{combined}"
    assert "congratulations" in combined.lower()
