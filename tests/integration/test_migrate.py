"""Integration tests for ansible-creator migrate."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tests.defaults import CREATOR_BIN


if TYPE_CHECKING:
    from tests.conftest import CliRunCallable


def test_migrate_molecule_cli(cli: CliRunCallable, tmp_path: Path) -> None:
    """Migrate a role-shaped integration target via the CLI."""
    collection = tmp_path / "ns" / "col"
    targets = collection / "tests" / "integration" / "targets" / "sample"
    tasks = targets / "tasks"
    tasks.mkdir(parents=True)
    (collection / "galaxy.yml").write_text("namespace: ns\nname: col\nversion: 0.1.0\n")
    (tasks / "main.yml").write_text("---\n- ansible.builtin.debug:\n    msg: ok\n")

    result = cli(
        f"{CREATOR_BIN} migrate molecule sample --path {collection}",
        env={"NO_COLOR": "1"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Moved" in result.stdout or "moved" in result.stdout.lower()

    scenario = collection / "extensions" / "molecule" / "sample"
    assert (scenario / "molecule.yml").is_file()
    assert (scenario / "converge.yml").is_file()
    assert (scenario / "roles" / "content" / "tasks" / "main.yml").is_file()
    assert not targets.exists()
    assert (collection / "extensions" / "molecule" / "MIGRATE_NEXT_STEPS.md").is_file()
    assert (collection / "extensions" / "molecule" / "config.yml").is_file()
    assert (collection / "extensions" / "molecule" / "inventory.yml").is_file()
    assert (collection / ".agents" / "skills" / "molecule-migrate-finalize" / "SKILL.md").is_file()
    assert "platforms:" not in (scenario / "molecule.yml").read_text()
    assert "name: content" in (scenario / "converge.yml").read_text()


def test_migrate_molecule_cli_all_and_keep(cli: CliRunCallable, tmp_path: Path) -> None:
    """Migrate all role-shaped targets while keeping ansible-test trees."""
    collection = tmp_path / "ns" / "col"
    targets = collection / "tests" / "integration" / "targets"
    for name in ("one", "two"):
        tasks = targets / name / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "main.yml").write_text("---\n- ansible.builtin.debug:\n    msg: ok\n")
    scripty = targets / "scripty"
    scripty.mkdir(parents=True)
    (scripty / "runme.sh").write_text("#!/bin/sh\necho hi\n")
    (collection / "galaxy.yml").write_text("namespace: ns\nname: col\nversion: 0.1.0\n")

    result = cli(
        f"{CREATOR_BIN} migrate molecule --all --keep-targets --path {collection}",
        env={"NO_COLOR": "1"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (targets / "one").is_dir()
    assert (targets / "two").is_dir()
    assert (targets / "scripty").is_dir()
    molecule_root = collection / "extensions" / "molecule"
    assert (molecule_root / "one" / "roles" / "content" / "tasks" / "main.yml").is_file()
    assert (molecule_root / "two" / "roles" / "content" / "tasks" / "main.yml").is_file()
    assert not (molecule_root / "scripty").exists()
    assert "ansible_connection: local" in (molecule_root / "inventory.yml").read_text()
