try:
    from jinja2 import Environment, StrictUndefined, PackageLoader

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


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
            loader=PackageLoader("ansible_creator", "templates"),
        )

    def render(self, template_name, contents):
        template = self.env.get_template(template_name)
        rendered_content = template.render(contents)
        return rendered_content
