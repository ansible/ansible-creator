"""A Jinja2 template engine."""
try:
    from jinja2 import Environment, StrictUndefined

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
from ..utils import get_file_contents


class Templar:
    """Class representing a Jinja2 template engine."""

    def __init__(self):
        """Instantiate the template engine."""
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
        """Render a template with provided data.

        :params template_name: Name of the template to load.
        :params data: Data to render template with.

        :returns: Templated content.
        """
        template_content = get_file_contents(
            directory="templates", filename=template_name
        )
        rendered_content = self.env.from_string(template_content).render(data)
        return rendered_content
