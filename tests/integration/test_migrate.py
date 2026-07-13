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
