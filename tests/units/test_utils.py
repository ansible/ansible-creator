"""Test the utils module."""

from pathlib import Path

import pytest

from ansible_creator.output import Output
from ansible_creator.templar import Templar
from ansible_creator.utils import Copier, expand_path


def test_expand_path() -> None:
    """Test expand_path utils."""
    home = Path.home().resolve()
    expected = home / "collections/ansible_collections/namespace/collection"
    assert expand_path("~/$DEV_WORKSPACE/namespace/collection") == expected
    assert expand_path("~") == home
    assert expand_path("foo") == Path.cwd() / "foo"
    assert expand_path("$HOME") == home
    assert expand_path("~/$HOME") == Path(f"{home}/{Path.home()}")


def test_copier(output: Output, tmp_path: Path) -> None:
    """Test Copier raises type error for path replacers.

    Args:
        output: Output object.
        tmp_path: Temporary directory.
    """
    templar = Templar()
    template_data = {"scm_org": True, "scm_project": False}
    copier = Copier(
        resources=["ansible_project"],
        resource_id="ansible_project",
        template_data=template_data,  # type: ignore[arg-type]
        dest=tmp_path,
        output=output,
        templar=templar,
    )
    with pytest.raises(TypeError, match="must be a string"):
        copier.copy_containers()
