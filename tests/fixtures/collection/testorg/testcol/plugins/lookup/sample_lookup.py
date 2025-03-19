# sample_lookup.py - A custom lookup plugin for Ansible.

# pylint: disable=E0401
# sample_lookup.py - A custom lookup plugin for Ansible.
# Author: Your Name (@username)
# Copyright 2020 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = """
    name: sample_lookup
    author: Your Name (@username)
    version_added: "1.0.0"
    short_description: A custom lookup plugin for Ansible.
    description:
      - This is a custom lookup plugin to provide lookup functionality.
    options:
      _terms:
        description: Terms to lookup
        required: True
    notes:
      - This is a scaffold template. Customize the plugin to fit your needs.
"""

EXAMPLES = """
- name: Example usage of sample_lookup
  ansible.builtin.debug:
    msg: "{{ lookup('sample_lookup', 'example_term') }}"
"""

RETURN = """
_list:
  description: The list of values found by the lookup
  type: list
"""

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError  # type: ignore
from ansible.plugins.lookup import LookupBase  # type: ignore
from ansible.utils.display import Display  # type: ignore

display = Display()


class LookupModule(LookupBase):  # type: ignore[misc]
    """
    Custom Ansible lookup plugin: sample_lookup
    A custom lookup plugin for Ansible.
    """

    def run(
        self,
        terms: List[str],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Dict[str, Any],
    ) -> list[str]:
        """
        Run the lookup with the specified terms.

        Args:
            terms: A list of terms to lookup.
            variables: Additional variables.
            **kwargs: Additional keyword arguments.

        Returns:
            list: A list of processed results.

        Raises:
            AnsibleError: If the 'terms' parameter is not a list.
        """
        if not isinstance(terms, list):
            raise AnsibleError("The 'terms' parameter must be a list.")

        display.vvv(f"Running sample_lookup lookup plugin with terms: {terms}")

        try:
            # Example processing logic - Replace this with actual lookup code
            result = [term.upper() for term in terms]

            display.vvv(f"Result from sample_lookup lookup: {result}")
            return result

        except Exception as e:
            raise AnsibleError(f"Error in sample_lookup plugin: {e}") from e
