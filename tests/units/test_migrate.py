# cspell: ignore dcmp
"""Unit tests for ansible-creator migrate."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.subcommands.migrate import Migrate


if TYPE_CHECKING:
    from ansible_creator.output import Output


def _write_role_target(targets_dir: Path, name: str, *, main_name: str = "main.yml") -> Path:
    target = targets_dir / name
    tasks = target / "tasks"
    tasks.mkdir(parents=True)
    (tasks / main_name).write_text("---\n- name: Ping\n  ansible.builtin.debug:\n    msg: hi\n")
    return target


def _seed_collection(tmp_path: Path) -> Path:
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
    return _seed_collection(tmp_path)


def _migrate_config(
    output: Output,
    path: Path,
    *,
    target_name: str = "",
    migrate_all: bool = False,
    keep_targets: bool = False,
    overwrite: bool = False,
    no_overwrite: bool = False,
) -> Config:
    return Config(
        creator_version="0.0.1",
        output=output,
        subcommand="migrate",
        migrate_type="molecule",
        target_name=target_name,
        migrate_all=migrate_all,
        keep_targets=keep_targets,
        path=str(path),
        overwrite=overwrite,
        no_overwrite=no_overwrite,
    )


def test_migrate_single_target_moves(collection_path: Path, output: Output) -> None:
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
    assert "prerun: false" in (
        collection_path / "extensions" / "molecule" / "config.yml"
    ).read_text()
    assert "ansible_connection: local" in (
        collection_path / "extensions" / "molecule" / "inventory.yml"
    ).read_text()
    molecule_yml = (scenario / "molecule.yml").read_text()
    assert "platforms:" not in molecule_yml
    assert "provisioner:" not in molecule_yml
    converge = (scenario / "converge.yml").read_text()
    assert "name: content" in converge
    assert "playbook_dir" not in converge


def test_migrate_all_skips_non_role(collection_path: Path, output: Output) -> None:
    Migrate(_migrate_config(output, collection_path, migrate_all=True)).run()

    molecule_root = collection_path / "extensions" / "molecule"
    assert (molecule_root / "alpha" / "roles" / "content" / "tasks" / "main.yml").is_file()
    assert (molecule_root / "beta" / "roles" / "content" / "tasks" / "main.yaml").is_file()
    assert not (molecule_root / "scripty").exists()
    assert (collection_path / "tests" / "integration" / "targets" / "scripty").is_dir()


def test_migrate_keep_targets(collection_path: Path, output: Output) -> None:
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
    with pytest.raises(CreatorError, match="target name or --all"):
        Migrate(_migrate_config(output, collection_path)).run()


def test_migrate_rejects_target_and_all(collection_path: Path, output: Output) -> None:
    with pytest.raises(CreatorError, match="not both"):
        Migrate(
            _migrate_config(output, collection_path, target_name="alpha", migrate_all=True),
        ).run()


def test_migrate_missing_target(collection_path: Path, output: Output) -> None:
    with pytest.raises(CreatorError, match="not found"):
        Migrate(_migrate_config(output, collection_path, target_name="missing")).run()


def test_migrate_no_overwrite(collection_path: Path, output: Output) -> None:
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
