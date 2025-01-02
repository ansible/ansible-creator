# hello_world.py - A custom action plugin for Ansible.
# Author: Your Name
# License: GPL-3.0-or-later
# pylint: disable=E0401

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING
from ansible.plugins.action import ActionBase  # type: ignore


if TYPE_CHECKING:
    from typing import Optional, Dict, Any


DOCUMENTATION = """
    name: hello_world
    author: Your Name
    version_added: "1.0.0"
    short_description: A custom action plugin for Ansible.
    description:
      - This is a custom action plugin to provide action functionality.
    notes:
      - This is a scaffold template. Customize the plugin to fit your needs.
"""

EXAMPLES = """
- name: Example Action Plugin
  hosts: localhost
  tasks:
    - name: Example hello_world plugin
      with_prefix:
        prefix: "Hello, World"
        msg: "Ansible!"
"""


class ActionModule(ActionBase):  # type: ignore[misc]
    """
    Custom Ansible action plugin: hello_world
    A custom action plugin for Ansible.
    """

    def run(
        self,
        tmp: Optional[str] = None,
        task_vars: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the action plugin.

        Args:
            tmp: Temporary path provided by Ansible for the module execution. Defaults to None.
            task_vars: Dictionary of task variables available to the plugin. Defaults to None.

        Returns:
            dict: Result of the action plugin execution.
        """
        # Get the task arguments
        if task_vars is None:
            task_vars = {}
        result = {}
        warnings: list[str] = []

        # Example processing logic - Replace this with actual action code
        result = super(ActionModule, self).run(tmp, task_vars)
        module_args = self._task.args.copy()
        result.update(
            self._execute_module(
                module_name="debug",
                module_args=module_args,
                task_vars=task_vars,
                tmp=tmp,
            ),
        )

        if warnings:
            if "warnings" in result:
                result["warnings"].extend(warnings)
            else:
                result["warnings"] = warnings
        return result
