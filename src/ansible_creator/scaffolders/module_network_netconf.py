"""Scaffolder class for module_network_netconf."""
from __future__ import annotations

from ansible_creator.scaffolders import NetworkScaffolderBase


class Scaffolder(NetworkScaffolderBase):
    """Scaffolder for module_network_netconf plugin type."""

    def run(self: Scaffolder) -> None:
        """Start scaffolding a module_network_netconf type plugin."""
