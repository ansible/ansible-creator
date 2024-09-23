"""Test the utils module."""

from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.types import TemplateData
from ansible_creator.utils import Copier, Walker, expand_path


if TYPE_CHECKING:
    import pytest

    from ansible_creator.output import Output


def test_expand_path() -> None:
    """Test expand_path utils."""
    home = Path.home().resolve()
    expected = home / "collections/ansible_collections/namespace/collection"
    assert expand_path("~/$DEV_WORKSPACE/namespace/collection") == expected
    assert expand_path("~") == home
    assert expand_path("foo") == Path.cwd() / "foo"
    assert expand_path("$HOME") == home
    assert expand_path("~/$HOME") == Path(f"{home}/{Path.home()}")


def test_skip_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: Output) -> None:
    """Test the skip dirs constant.

    Args:
        tmp_path: Temporary directory path.
        monkeypatch: Pytest monkeypatch fixture.
        output: Output class object.
    """
    monkeypatch.setattr("ansible_creator.utils.SKIP_DIRS", ["docker"])

    walker = Walker(
        resources=("common.devcontainer",),
        resource_id="common.devcontainer",
        dest=tmp_path,
        output=output,
        template_data=TemplateData(),
    )
    paths = walker.collect_paths()

    copier = Copier(
        output=output,
    )
    copier.copy_containers(paths)
    assert (tmp_path / ".devcontainer" / "podman").exists()
    assert not (tmp_path / ".devcontainer" / "docker").exists()


def test_overwrite(tmp_path: Path, output: Output) -> None:
    """Test Copier overwriting existing files.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.
    """
    walker = Walker(
        resources=("common.devcontainer",),
        resource_id="common.devcontainer",
        dest=tmp_path,
        output=output,
        template_data=TemplateData(),
    )
    paths = walker.collect_paths()

    copier = Copier(
        output=output,
    )
    copier.copy_containers(paths)

    # Replace podman with a file
    podman = tmp_path / ".devcontainer" / "podman"
    shutil.rmtree(podman)
    podman.write_text("This is an error")
    # Replace docker devcontainer with a directory
    docker = tmp_path / ".devcontainer" / "docker" / "devcontainer.json"
    docker.unlink()
    docker.mkdir()

    # Re-walk directory to generate warnings, but not make changes
    paths = walker.collect_paths()
    assert podman.is_file()
    assert docker.is_dir()

    # Re-copy to overwrite structure
    copier.copy_containers(paths)
    assert podman.is_dir()
    assert docker.is_file()
