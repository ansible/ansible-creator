# cspell: ignore dcmp
"""Unit tests for ansible-creator migrate."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.subcommands.migrate import Migrate


if TYPE_CHECKING:
    from pathlib import Path

    from ansible_creator.output import Output


def _write_role_target(targets_dir: Path, name: str, *, main_name: str = "main.yml") -> Path:
    """Create a minimal role-shaped integration target.

    Args:
        targets_dir: Parent targets directory.
        name: Target name.
        main_name: Tasks main filename.

    Returns:
        Path to the created target directory.
    """
    target = targets_dir / name
    tasks = target / "tasks"
    tasks.mkdir(parents=True)
    (tasks / main_name).write_text("---\n- name: Ping\n  ansible.builtin.debug:\n    msg: hi\n")
    return target


def _seed_collection(tmp_path: Path) -> Path:
    """Seed a collection with role-shaped and script-only targets.

    Args:
        tmp_path: Temporary directory path.

    Returns:
        Path to the seeded collection root.
    """
    collection = tmp_path / "ns" / "col"
    collection.mkdir(parents=True)
    (collection / "galaxy.yml").write_text("namespace: ns\nname: col\nversion: 1.0.0\n")
    targets = collection / "tests" / "integration" / "targets"
    targets.mkdir(parents=True)
    _write_role_target(targets, "alpha")
    _write_role_target(targets, "beta", main_name="main.yaml")
    script_only = targets / "scripty"
    script_only.mkdir()
    (script_only / "runme.sh").write_text("#!/bin/sh\necho hi\n")
    return collection


@pytest.fixture(name="collection_path")
def fixture_collection_path(tmp_path: Path) -> Path:
    """Provide a seeded collection path.

    Args:
        tmp_path: Temporary directory path.

    Returns:
        Path to the seeded collection root.
    """
    return _seed_collection(tmp_path)


def _migrate_config(  # noqa: PLR0913
    output: Output,
    path: Path,
    *,
    target_name: str = "",
    migrate_all: bool = False,
    keep_targets: bool = False,
    overwrite: bool = False,
    no_overwrite: bool = False,
    force: bool = False,
    migrate_type: str = "molecule",
    skip_collection_check: bool = False,
) -> Config:
    """Build a migrate Config for tests.

    Args:
        output: Output class object.
        path: Collection path.
        target_name: Optional target name.
        migrate_all: Whether to migrate all targets.
        keep_targets: Whether to copy instead of move.
        overwrite: Whether to overwrite existing scenarios.
        no_overwrite: Whether to refuse overwrites.
        force: Whether to force overwrite without prompting.
        migrate_type: Migrate destination type.
        skip_collection_check: Whether to skip galaxy.yml validation.

    Returns:
        Config instance for Migrate.
    """
    return Config(
        creator_version="0.0.1",
        output=output,
        subcommand="migrate",
        migrate_type=migrate_type,
        target_name=target_name,
        migrate_all=migrate_all,
        keep_targets=keep_targets,
        path=str(path),
        overwrite=overwrite,
        no_overwrite=no_overwrite,
        force=force,
        skip_collection_check=skip_collection_check,
    )


def test_migrate_single_target_moves(collection_path: Path, output: Output) -> None:
    """Move one target into an ansible-native scenario layout.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha")).run()

    scenario = collection_path / "extensions" / "molecule" / "alpha"
    assert (scenario / "molecule.yml").is_file()
    assert (scenario / "converge.yml").is_file()
    assert (scenario / "roles" / "content" / "tasks" / "main.yml").is_file()
    assert not (collection_path / "tests" / "integration" / "targets" / "alpha").exists()
    assert (collection_path / "extensions" / "molecule" / "MIGRATE_NEXT_STEPS.md").is_file()
    assert (
        collection_path / ".agents" / "skills" / "molecule-migrate-finalize" / "SKILL.md"
    ).is_file()
    assert (collection_path / "extensions" / "molecule" / "config.yml").is_file()
    assert (collection_path / "extensions" / "molecule" / "inventory.yml").is_file()
    assert (
        "prerun: false" in (collection_path / "extensions" / "molecule" / "config.yml").read_text()
    )
    assert (
        "ansible_connection: local"
        in (collection_path / "extensions" / "molecule" / "inventory.yml").read_text()
    )
    molecule_yml = (scenario / "molecule.yml").read_text()
    assert "platforms:" not in molecule_yml
    assert "provisioner:" not in molecule_yml
    converge = (scenario / "converge.yml").read_text()
    assert "name: content" in converge
    assert "playbook_dir" not in converge


def test_migrate_all_skips_non_role(collection_path: Path, output: Output) -> None:
    """Migrate all role-shaped targets and skip script-only ones.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, migrate_all=True)).run()

    molecule_root = collection_path / "extensions" / "molecule"
    assert (molecule_root / "alpha" / "roles" / "content" / "tasks" / "main.yml").is_file()
    assert (molecule_root / "beta" / "roles" / "content" / "tasks" / "main.yaml").is_file()
    assert not (molecule_root / "scripty").exists()
    assert (collection_path / "tests" / "integration" / "targets" / "scripty").is_dir()


def test_migrate_keep_targets(collection_path: Path, output: Output) -> None:
    """Copy targets into scenarios when --keep-targets is set.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(
        _migrate_config(output, collection_path, target_name="alpha", keep_targets=True),
    ).run()

    assert (collection_path / "tests" / "integration" / "targets" / "alpha").is_dir()
    assert (
        collection_path
        / "extensions"
        / "molecule"
        / "alpha"
        / "roles"
        / "content"
        / "tasks"
        / "main.yml"
    ).is_file()


def test_migrate_requires_target_or_all(collection_path: Path, output: Output) -> None:
    """Require either a target name or --all.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    with pytest.raises(CreatorError, match="target name or --all"):
        Migrate(_migrate_config(output, collection_path)).run()


def test_migrate_rejects_target_and_all(collection_path: Path, output: Output) -> None:
    """Reject specifying both a target name and --all.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    with pytest.raises(CreatorError, match="not both"):
        Migrate(
            _migrate_config(output, collection_path, target_name="alpha", migrate_all=True),
        ).run()


def test_migrate_missing_target(collection_path: Path, output: Output) -> None:
    """Fail when the named target does not exist.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    with pytest.raises(CreatorError, match="not found"):
        Migrate(_migrate_config(output, collection_path, target_name="missing")).run()


def test_migrate_no_overwrite(collection_path: Path, output: Output) -> None:
    """Fail when scenario paths exist and --no-overwrite is set.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="beta", keep_targets=True)).run()
    with pytest.raises(CreatorError, match="--no-overwrite"):
        Migrate(
            _migrate_config(
                output,
                collection_path,
                target_name="beta",
                keep_targets=True,
                no_overwrite=True,
            ),
        ).run()


def test_migrate_overwrite(collection_path: Path, output: Output) -> None:
    """Overwrite an existing scenario when --overwrite is set.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="beta", keep_targets=True)).run()
    Migrate(
        _migrate_config(
            output,
            collection_path,
            target_name="beta",
            keep_targets=True,
            overwrite=True,
        ),
    ).run()
    assert (
        collection_path
        / "extensions"
        / "molecule"
        / "beta"
        / "roles"
        / "content"
        / "tasks"
        / "main.yaml"
    ).is_file()


def test_migrate_unsupported_type(collection_path: Path, output: Output) -> None:
    """Reject unsupported migrate types.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    with pytest.raises(CreatorError, match="Unsupported migrate type"):
        Migrate(
            _migrate_config(output, collection_path, target_name="alpha", migrate_type="galaxy"),
        ).run()


def test_migrate_path_missing(tmp_path: Path, output: Output) -> None:
    """Fail when the collection path does not exist.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.
    """
    missing = tmp_path / "does-not-exist"
    with pytest.raises(CreatorError, match="does not exist"):
        Migrate(_migrate_config(output, missing, target_name="alpha")).run()


def test_migrate_not_a_collection(tmp_path: Path, output: Output) -> None:
    """Fail when the path is not a collection root.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.
    """
    path = tmp_path / "not-a-collection"
    path.mkdir()
    with pytest.raises(CreatorError, match="not a valid Ansible collection"):
        Migrate(_migrate_config(output, path, target_name="alpha")).run()


def test_migrate_skip_collection_check(tmp_path: Path, output: Output) -> None:
    """Allow migration without galaxy.yml when skip_collection_check is set.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.
    """
    collection = tmp_path / "loose"
    targets = collection / "tests" / "integration" / "targets"
    targets.mkdir(parents=True)
    _write_role_target(targets, "alpha")

    Migrate(
        _migrate_config(
            output,
            collection,
            target_name="alpha",
            skip_collection_check=True,
        ),
    ).run()
    assert (
        collection
        / "extensions"
        / "molecule"
        / "alpha"
        / "roles"
        / "content"
        / "tasks"
        / "main.yml"
    ).is_file()


def test_migrate_missing_targets_dir(tmp_path: Path, output: Output) -> None:
    """Fail when tests/integration/targets is missing.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.
    """
    collection = tmp_path / "ns" / "col"
    collection.mkdir(parents=True)
    (collection / "galaxy.yml").write_text("namespace: ns\nname: col\nversion: 1.0.0\n")
    with pytest.raises(CreatorError, match="No integration targets directory"):
        Migrate(_migrate_config(output, collection, migrate_all=True)).run()


def test_migrate_all_none_role_shaped(tmp_path: Path, output: Output) -> None:
    """Fail when --all finds no role-shaped targets.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.
    """
    collection = tmp_path / "ns" / "col"
    targets = collection / "tests" / "integration" / "targets"
    targets.mkdir(parents=True)
    (collection / "galaxy.yml").write_text("namespace: ns\nname: col\nversion: 1.0.0\n")
    script_only = targets / "scripty"
    script_only.mkdir()
    (script_only / "runme.sh").write_text("#!/bin/sh\necho hi\n")

    with pytest.raises(CreatorError, match="No role-shaped"):
        Migrate(_migrate_config(output, collection, migrate_all=True)).run()


def test_migrate_prompt_declines_overwrite(
    collection_path: Path,
    output: Output,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Abort when the overwrite prompt is declined.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha", keep_targets=True)).run()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(CreatorError, match="aborted due to existing content"):
        Migrate(
            _migrate_config(output, collection_path, target_name="alpha", keep_targets=True),
        ).run()


def test_migrate_prompt_accepts_overwrite(
    collection_path: Path,
    output: Output,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overwrite when the overwrite prompt is accepted.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha", keep_targets=True)).run()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    Migrate(
        _migrate_config(output, collection_path, target_name="alpha", keep_targets=True),
    ).run()
    assert (
        collection_path
        / "extensions"
        / "molecule"
        / "alpha"
        / "roles"
        / "content"
        / "tasks"
        / "main.yml"
    ).is_file()


def test_migrate_force_overwrite(collection_path: Path, output: Output) -> None:
    """Overwrite without prompting when force is set.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha", keep_targets=True)).run()
    Migrate(
        _migrate_config(
            output,
            collection_path,
            target_name="alpha",
            keep_targets=True,
            force=True,
        ),
    ).run()
    assert (
        collection_path
        / "extensions"
        / "molecule"
        / "alpha"
        / "roles"
        / "content"
        / "tasks"
        / "main.yml"
    ).is_file()


def test_migrate_skips_rewriting_shared_config(collection_path: Path, output: Output) -> None:
    """Leave existing shared config and inventory untouched on later runs.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha", keep_targets=True)).run()
    config_path = collection_path / "extensions" / "molecule" / "config.yml"
    inventory_path = collection_path / "extensions" / "molecule" / "inventory.yml"
    config_path.write_text("# custom shared config\n")
    inventory_path.write_text("# custom inventory\n")

    Migrate(_migrate_config(output, collection_path, target_name="beta", keep_targets=True)).run()
    assert config_path.read_text() == "# custom shared config\n"
    assert inventory_path.read_text() == "# custom inventory\n"


def test_migrate_skill_no_overwrite_keeps_custom(
    collection_path: Path,
    output: Output,
) -> None:
    """Keep a customized skill file when --no-overwrite is set.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha", keep_targets=True)).run()
    skill = collection_path / ".agents" / "skills" / "molecule-migrate-finalize" / "SKILL.md"
    skill.write_text("# custom skill\n")

    Migrate(
        _migrate_config(
            output,
            collection_path,
            target_name="beta",
            keep_targets=True,
            no_overwrite=True,
        ),
    ).run()
    assert skill.read_text() == "# custom skill\n"


def test_migrate_skill_unchanged_is_left_alone(collection_path: Path, output: Output) -> None:
    """Do not rewrite an identical skill file on later migrations.

    Args:
        collection_path: Seeded collection path.
        output: Output class object.
    """
    Migrate(_migrate_config(output, collection_path, target_name="alpha", keep_targets=True)).run()
    skill = collection_path / ".agents" / "skills" / "molecule-migrate-finalize" / "SKILL.md"
    original = skill.read_text()

    Migrate(_migrate_config(output, collection_path, target_name="beta", keep_targets=True)).run()
    assert skill.read_text() == original
