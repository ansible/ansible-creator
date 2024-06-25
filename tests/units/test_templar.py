"""Tests for templar."""

from ansible_creator.templar import Templar


def test_templar() -> None:
    """Test templar."""
    templar = Templar()
    data = {"key": "value"}
    template = "{{ key }}"
    assert templar.render_from_content(template, data) == "value"


def test_templar_json_simple() -> None:
    """Test templar json with a simple structure."""
    templar = Templar()
    data = {"key": "value"}
    template = "{{ key | json }}"
    assert templar.render_from_content(template, data) == '"value"'


def test_templar_json_complex() -> None:
    """Test templar json with a complex structure."""
    templar = Templar()
    data = {"key": {"sub_key": ["value", "value2"]}}
    template = "{{ key | json }}"
    assert templar.render_from_content(template, data) == '{"sub_key": ["value", "value2"]}'
