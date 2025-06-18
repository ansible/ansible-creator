"""Tests for templar."""

from __future__ import annotations

from ansible_creator.templar import Templar
from ansible_creator.types import TemplateData


def test_templar() -> None:
    """Test templar."""
    templar = Templar()
    data = TemplateData(collection_name="test")
    template = "{{ collection_name }}"
    assert templar.render_from_content(template, data) == "test"


def test_templar_json_simple() -> None:
    """Test templar json with a simple structure."""
    templar = Templar()
    data = TemplateData(recommended_extensions=["value"])
    template = "{{ recommended_extensions | json }}"
    assert templar.render_from_content(template, data) == '["value"]'


def test_templar_json_complex() -> None:
    """Test templar json with a complex structure."""
    templar = Templar()
    data = TemplateData(additions={"key": {"key": {"key": True}}})
    template = "{{ additions | json }}"
    assert templar.render_from_content(template, data) == '{"key": {"key": {"key": true}}}'
