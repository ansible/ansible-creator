# sample_action.py - A custom action plugin for Ansible.
# Author: Your Name
# License: GPL-3.0-or-later
# pylint: disable=E0401

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING
from ansible_collections.ansible.utils.plugins.module_utils.common.argspec_validate import (  # type: ignore
    AnsibleArgSpecValidator,
)
from ansible_collections.ansible.utils.plugins.modules.fact_diff import DOCUMENTATION  # type: ignore
from ansible.plugins.action import ActionBase  # type: ignore


if TYPE_CHECKING:
    from typing import Optional, Dict, Any


class ActionModule(ActionBase):  # type: ignore[misc]
    """
    Custom Ansible action plugin: sample_action
    A custom action plugin for Ansible.
    """

    def _check_argspec(self, result: dict[str, Any]) -> None:
        aav = AnsibleArgSpecValidator(
            data=self._task.args,
            schema=DOCUMENTATION,
            schema_format="doc",
            name=self._task.action,
        )
        valid, errors, self._task.args = aav.validate()
        if not valid:
            result["failed"] = True
            result["msg"] = errors

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
        self._check_argspec(result)

        # Copy the task arguments
        module_args = self._task.args.copy()

        prefix = module_args.get("prefix", "DefaultPrefix")
        message = module_args.get("msg", "No message provided")
        module_args["msg"] = f"{prefix}: {message}"

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
