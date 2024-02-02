"""A Jinja2 template engine."""

from __future__ import annotations


try:
    from jinja2 import Environment, StrictUndefined

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


class Templar:
    """Class representing a Jinja2 template engine."""

    def __init__(self: Templar) -> None:
        """Instantiate the template engine.

        :raises ImportError: When jinja2 is not installed.
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

    def render_from_content(self: Templar, template: str, data: dict) -> str:
        """Render a template with provided data.

        :param template: The template to load and render.
        :param data: Data to render template with.

        :returns: Templated content.
        """
        return self.env.from_string(template).render(data)
