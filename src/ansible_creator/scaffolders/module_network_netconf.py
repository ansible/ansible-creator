"""Scaffolder class for module_network_netconf."""

from ansible_creator.scaffolders import ScaffolderBase


class Scaffolder(ScaffolderBase):
    """Scaffolder for module_network_netconf plugin type."""

    def __init__(self, **args):
        """Instantiate an object of this class.

        :param args: A dictionary containing scaffolding data.
        """
        super().__init__(**args)
        self.resource = args["resource"]

    def run(self):
        """Start scaffolding a module_network_netconf type plugin."""
