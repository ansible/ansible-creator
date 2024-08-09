"""Test the utils module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.types import TemplateData
from ansible_creator.utils import Copier, expand_path


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
    copier = Copier(
        resources=["common.devcontainer"],
        resource_id="common.devcontainer",
        dest=tmp_path,
        output=output,
        template_data=TemplateData(),
    )
    copier.copy_containers()
    assert (tmp_path / ".devcontainer" / "podman").exists()
    assert not (tmp_path / ".devcontainer" / "docker").exists()
