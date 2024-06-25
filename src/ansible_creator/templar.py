"""A Jinja2 template engine."""

from __future__ import annotations

import json

from dataclasses import asdict
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ansible_creator.types import TemplateData


try:
    from jinja2 import Environment, StrictUndefined

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


class Templar:
    """Class representing a Jinja2 template engine."""

    def __init__(self: Templar) -> None:
        """Instantiate the template engine.

        Raises:
            ImportError: when jinja2 is not installed.
        """
        if not HAS_JINJA2:
            msg = (
                "jinja2 is required but does not appear to be installed."
                "It can be installed using `pip install jinja2`"
            )
            raise ImportError(
                msg,
            )
        self.env: Environment = Environment(  # noqa: S701
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        self.env.filters["json"] = json.dumps

    def render_from_content(self: Templar, template: str, data: TemplateData) -> str:
        """Render a template with provided data.

        Args:
            template: The template to load and render.
            data: Data to render template with.

        Returns:
            Templated content.
        """
        return self.env.from_string(template).render(asdict(data))
