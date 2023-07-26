try:
    from jinja2 import Environment, StrictUndefined

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
from importlib import resources


class Templar:
    def __init__(self):
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
        template_content = self.get_template_content(template_name)
        rendered_content = self.env.from_string(template_content).render(data)
        return rendered_content

    def get_template_content(self, template_name):
        package = "ansible_creator.templates"

        with resources.files(package).joinpath(template_name).open(
            "r", encoding="utf-8"
        ) as fh:
            content = fh.read()

        return content
