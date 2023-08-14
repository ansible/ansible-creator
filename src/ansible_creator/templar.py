"""A Jinja2 template engine."""
try:
    from jinja2 import Environment, StrictUndefined

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
from .utils import get_file_contents


class Templar:
    """Class representing a Jinja2 template engine."""

    def __init__(self):
        """Instantiate the template engine.

        :raises ImportError: When jinja2 is not installed.
        """
        if not HAS_JINJA2:
            raise ImportError(
                "jinja2 is required but does not appear to be installed.  "
                "It can be installed using `pip install jinja2`"
            )
        self.env = Environment(
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def render(self, template_name, data):
        """Load template from a file and render with provided data.

        :param template_name: Name of the template to load.
        :param data: Data to render template with.

        :returns: Templated content.
        """
        template_content = get_file_contents(
            directory="templates", filename=template_name
        )
        return self.render_from_content(template=template_content, data=data)

    def render_from_content(self, template, data):
        """Render a template with provided data.

        :param template: The template to load and render.
        :param data: Data to render template with.

        :returns: Templated content.
        """
        rendered_content = self.env.from_string(template).render(data)
        return rendered_content
