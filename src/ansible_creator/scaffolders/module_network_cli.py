"""Scaffolder class for module_network_cli."""
from __future__ import annotations

from ansible_creator.scaffolders import NetworkScaffolderBase
from ansible_creator.utils import copy_container


class Scaffolder(NetworkScaffolderBase):
    """Scaffolder for module_network_cli plugin type."""

    def run(self: Scaffolder) -> None:
        """Start scaffolding a module_network_cli type plugin."""
        super().run()

        copy_container(
            source="module_network_cli",
            dest=self.collection_path,
            templar=self._templar,
            template_data=self.template_data,
        )
