"""Scaffolder class for module_network_cli."""

from importlib import resources

from ansible_creator.scaffolders import ScaffolderBase
from ansible_creator.utils import copy_container


class Scaffolder(ScaffolderBase):
    """Scaffolder for module_network_cli plugin type."""

    def __init__(self, **args):
        """Instantiate an object of this class.

        :param args: A dictionary containing scaffolding data.
        """
        super().__init__(**args)
        self.resource = args["resource"]

    def run(self):
        """Start scaffolding a module_network_cli type plugin."""
        import_path = (
            f"ansible_collections.{self.namespace}.{self.collection_name}."
            "plugins.module_utils.network"
        )

        copy_container(
            src=resources.files("ansible_creator.resources.module_network_cli"),
            dest=self.collection_path,
            root="module_network_cli",
            templar=self._templar,
            template_data={
                "argspec": str(self.generate_argspec()),
                "import_path": import_path,
                "namespace": self.namespace,
                "collection_name": self.collection_name,
                "resource": self.resource,
                "name": self.plugin_name,
                "network_os": self.collection_name,
                "documentation": self.docstring,
            },
        )
