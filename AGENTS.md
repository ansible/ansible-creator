# AGENTS.md

This file provides Ansible best practices guidance for AI agents when writing or reviewing Ansible automation code. It is derived from the "Good Practices for Ansible" (GPA) documentation.

## Table of Contents

- [Guiding Principles](#guiding-principles)
- [Code Structure and Organization](#code-structure-and-organization)
- [Naming Conventions](#naming-conventions)
- [YAML and Jinja2 Syntax](#yaml-and-jinja2-syntax)
- [Ansible-Specific Guidelines](#ansible-specific-guidelines)
- [Roles Best Practices](#roles-best-practices)
- [Playbooks Best Practices](#playbooks-best-practices)
- [Inventories and Variables](#inventories-and-variables)
- [Collections Best Practices](#collections-best-practices)
- [Plugins Best Practices](#plugins-best-practices)

## Guiding Principles

**The Zen of Ansible** (by Tim Appnel):

- Ansible is not Python
- YAML sucks for coding
- Playbooks are not for programming
- Ansible users are (most probably) not programmers
- Clear is better than cluttered
- Concise is better than verbose
- Simple is better than complex
- Readability counts
- Helping users get things done matters most
- User experience beats ideological purity
- "Magic" conquers the manual
- When giving users options, always use convention over configuration
- Declarative is always better than imperative - most of the time
- Focus avoids complexity
- Complexity kills productivity
- If the implementation is hard to explain, it's a bad idea
- Every shell command and UI interaction is an opportunity to automate
- Just because something works, doesn't mean it can't be improved
- Friction should be eliminated whenever possible
- Automation is a continuous journey that never ends

## Code Structure and Organization

### Structure Hierarchy

Follow this structural hierarchy:

1. **Landscape**: Complete deployment (workflow or "playbook of playbooks")
2. **Type**: One per managed host (unique playbook). Each managed host has one and only one type
3. **Function**: Reusable roles
4. **Component**: Task files within roles or sub-roles for large functions

### When to Use What

- **Workflows**: For complete landscapes that deploy multiple types at once
- **Playbooks**: One per type; should be simple lists of roles
- **Roles**: For functions that can be reused across types
- **Task files**: For components within roles to improve maintainability

### Key Rule

If functions are defined for re-usability, components are for maintainability/readability. A re-usable component might be promoted to a function.

## Naming Conventions

### General Rules

1. Use `snake_case_naming_schemes` for all YAML/Python files, variables, arguments, repositories, and dictionary keys
2. Use valid Python identifiers - no special characters except underscore
3. Use mnemonic, descriptive names - don't shorten unnecessarily
4. Follow pattern: `object[_feature]_action` (ensures proper sorting)
5. Avoid numbering roles and playbooks
6. Name all tasks, plays, and task blocks
7. Write task names in imperative (e.g., "Ensure service is running")
8. Avoid abbreviations; use capital letters for unavoidable abbreviations

### Role-Specific Naming

1. **Prefix all role variables** with role name: `rolename_variable` not `variable`
2. **Internal variables** use double underscore prefix: `__rolename_internal_var`
3. **Modules in roles** need role prefix: `rolename_module`
4. **Tags in roles** should be prefixed with role name or unique descriptive prefix
5. **No dashes in role names** - causes issues with collections

### Task Naming

- Dynamic task names: put Jinja2 templates at the **end** of the string
  - ✅ `Manage the disk device {{ storage_device_name }}`
  - ❌ `Manage {{ storage_device_name }}, the disk device`
- Don't use variables in play names - they don't expand properly
- Don't use loop variables (`item`) in task names - they don't expand properly

## YAML and Jinja2 Syntax

### Formatting

1. **Indent at two spaces**
2. **Indent list contents beyond the list definition**:
   ```yaml
   example_list:
     - element_1
     - element_2
   ```

3. **Split long lines** using YAML folding sign `>-` (not `>`):
   ```yaml
   - name: Call a very long command line
     ansible.builtin.command: >-
       echo Lorem ipsum dolor sit amet, consectetur adipiscing elit.
       Maecenas mollis, ante in cursus congue.
   ```

4. **Break long `when` conditions** into lists:
   ```yaml
   when:
     - myvar is defined
     - myvar | bool
   ```

### File Extensions and Syntax

1. Use `.yml` extension, not `.yaml`
2. Use double quotes for YAML strings
3. Use single quotes for Jinja2 strings
4. Don't use quotes for module keywords (`present`, `absent`) but do use them for user strings
5. Spell out task arguments in YAML style, not `key=value`:
   ```yaml
   # ✅ Do this:
   - name: Print a message
     ansible.builtin.debug:
       msg: This is correct

   # ❌ Don't do this:
   - name: Print a message
     ansible.builtin.debug: msg="Wrong format"
   ```

### Boolean Values

Use `true` and `false` (YAML 1.2 compliant), not `yes`/`no` or `True`/`False`

### Jinja2 Templates

1. Use single space separating template markers: `{{ variable_name }}`
2. Break lengthy templates into multiple files for distinct logical sections
3. Use Jinja for text/semi-structured data, not structured data manipulation
4. Use filter plugins for data transformations instead of complex Jinja

### Line Wrapping

1. Wrap long Jinja expressions across multiple lines:
   ```yaml
   - name: Wrap long expressions
     foo: "{{ a_very.long_variable.name |
       somefilter('with', 'many', 'arguments') |
       another_filter | list }}"
   ```

2. Start with `{{` on new line if first line is too long:
   ```yaml
   very_indented_foo: "{{
     a_very.long_variable.name |
     somefilter('args') | list }}"
   ```

3. Use backslash escapes for long strings without spaces:
   ```yaml
   - name: Use a very long URL
     uri:
       url: "https://{{ hostname }}:\
         {{ port }}\
         {{ uri }}"
   ```

## Ansible-Specific Guidelines

### Idempotency and Check Mode

1. **All tasks must be idempotent** - no changes on second run with same parameters
2. **Support check mode** - roles should work in check mode and report changes accurately
3. Use `changed_when:` with `command`/`shell` modules
4. Use proper modules instead of commands when possible

### Comments

- Avoid comments in playbooks when possible
- Make task `name` values descriptive enough
- Variables are documented in `defaults` and `vars` directories
- If using `command`/`shell`, add justifying comment

### Module and Filter Usage

1. **Prefer specific modules** over `command`/`shell`
2. **Use meta modules** when possible (`service` instead of `systemd`, `package` instead of `yum`)
3. **Avoid `lineinfile`** where feasible - use `template`, `ini_file`, `blockinfile`, `xml`, or specific modules
4. **Use `template` over `copy`** for most file pushes (append `.j2` to template filenames)
5. Keep filenames close to destination system names

### Variables

1. **Use `| bool` filter** with bare variables in `when` conditions
2. **Use bracket notation** instead of dot notation: `item['key']` not `item.key`
3. **Don't override role defaults/vars** using `set_fact` - use different name
4. **Use smallest scope** for variables - limit use of `set_fact` (facts are global)
5. **Use type filters** for type safety: `float`, `int`, `bool`
6. **Don't use `eq`, `equalto`, or `==` Jinja tests** - use `match`, `search`, or `regex` instead (EL7 compatibility)

### Control Flow

1. **Don't use `meta: end_play`** - it aborts whole play, not just host. Use `meta: end_host` if needed
2. **Avoid `when: foo_result is changed`** - use handlers instead
3. **Use include/import statements** to reduce repetition
4. **Beware of `ignore_errors: true`** - especially in blocks with asserts

### Performance

1. **Avoid iterative `package` calls** - use list: `name: "{{ foo_packages }}"`
2. Apply same principle to other modules that accept lists

## Roles Best Practices

### Design Principles

1. **Focus on functionality**, not software implementation
2. **Design for specific, guaranteed outcomes** - limit scope to that outcome
3. **Place common content** in reusable "common" role within collections
4. **Author loosely coupled, hierarchical content**

### Role Structure

1. Use `ansible-galaxy init` structure for consistency
2. Use semantic versioning (0.y.z before stable)
3. Package roles in collections for distribution

### Naming Parameters

1. All defaults and arguments prefixed with role name: `rolename_parameter`
2. Internal variables prefixed with double underscore: `__rolename_internal`
3. Provider variable format: `rolename_provider`
4. OS default provider: `rolename_provider_os_default`

### Supporting Multiple Platforms

1. **Avoid testing distribution/version in tasks**
2. **Add variable files** to `vars/` for each supported distribution/version
3. **Use `tasks/set_vars.yml`** pattern:
   ```yaml
   - name: Ensure ansible_facts used by role
     setup:
       gather_subset: min
     when: not ansible_facts.keys() | list |
       intersect(__rolename_required_facts) == __rolename_required_facts

   - name: Set platform/version specific variables
     include_vars: "{{ __rolename_vars_file }}"
     loop:
       - "{{ ansible_facts['os_family'] }}.yml"
       - "{{ ansible_facts['distribution'] }}.yml"
       - "{{ ansible_facts['distribution'] }}_{{ ansible_facts['distribution_major_version'] }}.yml"
       - "{{ ansible_facts['distribution'] }}_{{ ansible_facts['distribution_version'] }}.yml"
     vars:
       __rolename_vars_file: "{{ role_path }}/vars/{{ item }}"
     when: __rolename_vars_file is file
   ```

4. **Platform-specific tasks** use `lookup('first_found')`:
   ```yaml
   - name: Perform platform/version specific tasks
     include_tasks: "{{ lookup('first_found', __rolename_ff_params) }}"
     vars:
       __rolename_ff_params:
         files:
           - "{{ ansible_facts['distribution'] }}_{{ ansible_facts['distribution_version'] }}.yml"
           - "{{ ansible_facts['distribution'] }}_{{ ansible_facts['distribution_major_version'] }}.yml"
           - "{{ ansible_facts['distribution'] }}.yml"
           - "{{ ansible_facts['os_family'] }}.yml"
           - "default.yml"
         paths:
           - "{{ role_path }}/tasks/setup"
   ```

5. **Use bracket notation** for facts: `ansible_facts['distribution']` not `ansible_distribution`

### Provider Support

1. Define `rolename_provider` variable
2. Detect current provider if not defined
3. Respect existing provider before changing
4. Select appropriate default for OS version
5. Set `rolename_provider_os_default` variable

### Templates

1. Add `{{ ansible_managed | comment }}` at top
2. Don't include timestamps (breaks change reporting)
3. Use `backup: true` until user requests configurability
4. Use `{{ role_path }}/subdir/` prefix with variable filenames

### Vars vs Defaults

1. **`defaults/main.yml`**: All external arguments with default values (document copiously)
2. **`vars/main.yml`**: Large lists, magic values, constants (avoid default values here - high precedence)
3. **Comment out** variables in `defaults/main.yml` if no meaningful default exists
4. **Example pattern**: `foo_packages` in `vars/main.yml`, `foo_extra_packages` in `defaults/main.yml`

### Documentation

1. Create meaningful README in role root
2. Include example playbooks
3. List inbound/outbound argument specifications
4. Document user-facing capabilities
5. Specify idempotent status (True/False)
6. Use fully qualified role names in examples
7. Use RFC-compliant addresses in examples

### Anti-Patterns

1. **Don't use host group names** - use variables instead (allows multiple clusters per inventory)
2. **Prefix task names** in sub-task files: `- name: sub | Some task description`

### Argument Validation

Use `meta/argument_specs.yml` (Ansible 2.11+):
```yaml
argument_specs:
  main:
    short_description: Role description.
    options:
      string_arg1:
        description: string argument description.
        type: "str"
        default: "x"
        choices: ["x", "y"]
      dict_arg1:
        description: dict argument description.
        type: dict
        required: True
```

## Playbooks Best Practices

### Simplicity

1. **Keep playbooks simple** - put logic in roles
2. **Limit playbooks to lists of roles** when possible:
   ```yaml
   ---
   - name: A playbook can solely be a list of roles
     hosts: all
     gather_facts: false
     become: false
     roles:
       - role1
       - role2
       - role3
   ```

### Structure

1. **Use either `tasks` or `roles` section, not both** - execution order isn't obvious
2. Use `roles` section for static imports
3. Use `tasks` section with `include_role`/`import_role` for dynamic inclusion

### Tags

1. **Limit tags to two types**:
   - Tags matching role names (for switching roles on/off)
   - Specific tags for meaningful purposes
2. **Document all tags**
3. **Don't create tags that can't be used standalone**
4. **Each tag should achieve meaningful result alone**

Example with `import_role`:
```yaml
- name: Import role1
  ansible.builtin.import_role:
    name: role1
  tags:
    - role1
    - deploy
```

Example with `include_role` (requires `apply`):
```yaml
- name: Include role1
  include_role:
    name: role1
    apply:
      tags:
        - role1
        - deploy
  tags:
    - role1
    - deploy
```

### Debug Messages

Use verbosity parameter:
```yaml
- name: This appears only with -vv or higher
  debug:
    msg: "Debug information"
    verbosity: 2
```

## Inventories and Variables

### Single Source of Truth (SSOT)

1. **Identify SSOTs** for each piece of information
2. **Use dynamic inventory sources** to combine multiple SSOTs
3. **Keep only unique data static** in inventory
4. Three SSOT types:
   - Technical (cloud APIs, hypervisors - provide "As-Is" info)
   - Managed (CMDB - provides "To-Be" info)
   - Inventory itself (for data not elsewhere)

### As-Is vs To-Be

1. **Clearly differentiate** between discovered ("As-Is") and managed ("To-Be") information
2. **Focus inventory on managed information** (desired state)
3. **Don't confuse facts (As-Is) with variables (To-Be)**
4. Use discovered info only when it's not part of desired state

### Inventory Structure

Use structured directory, not single file:

```
inventory_example/
├── dynamic_inventory_plugin.yml
├── dynamic_inventory_script.py
├── groups_and_hosts
├── group_vars/
│   ├── all/
│   │   └── ansible.yml
│   └── group_name/
│       └── role_name.yml
└── host_vars/
    └── host.example.com/
        ├── ansible.yml
        └── role_name.yml
```

1. Variable file names match role names (except `ansible.yml`)
2. Can use subdirectories in `host_vars`/`group_vars` for complex setups
3. Keep `groups_and_hosts` file free of variables

### Loop Over Hosts

**Don't create lists of hosts** - use inventory capabilities instead:

Benefits of using inventory:
1. Easier to maintain than lists
2. Avoids duplicating information
3. Ansible handles parallelization/throttling automatically
4. Can use `--limit` to restrict execution
5. Can use groups and patterns

❌ Bad pattern:
```yaml
# Manager has list of hosts in variables
loop: "{{ manager_hosts }}"
```

✅ Good pattern:
```yaml
# Hosts are in inventory with proper group_vars
# Play runs against inventory hosts in parallel
hosts: managed_hosts
```

### Variable Types

**Restrict usage** to reduce complexity (from 22 precedence levels to 8):

1. **Role defaults** (`defaults/main.yml`) - can be overwritten by anything
2. **Inventory vars** - represent desired state
3. **Host facts** - represent current state (shouldn't collide with inventory vars)
4. **Role vars** (`vars/main.yml`) - constants, shouldn't collide with inventory vars
5. **Scoped vars** (block/task level) - local to scope
6. **Runtime vars** (`register`, `set_fact`) - current automation state
7. **Scoped params** (role/include level) - avoid to limit surprises
8. **Extra vars** - overwrite everything (use sparingly)

### Variable Best Practices

1. **Avoid playbook/play variables** and `include_vars` - use inventory instead
2. **Avoid scoped variables** unless needed for runtime (loops, temporary vars)
3. **Prefer inventory variables over extra vars** for desired state
4. **Use extra vars only for**:
   - Troubleshooting/debugging
   - Validation purposes
   - Safety confirmations (`are_you_really_sure: true`)
   - Simulating fact values for testing

## Collections Best Practices

### Structure

1. **Collections at type or landscape level** - not individual roles
2. **Create "common" role** for content shared across multiple roles
3. **Author loosely coupled, hierarchical content**

### Variables

Use implicit collection variables referenced in role defaults:

```yaml
# Collection: mycollection
# Role: alpha - defaults/main.yml
alpha_job_name: 'some text'  # Role-specific
alpha_controller_username: "{{ mycollection_controller_username }}"  # Collection-wide
alpha_no_log: "{{ mycollection_no_log | default('true') }}"  # Collection-wide with default
```

Benefits:
- Avoids variable collisions when reusing roles
- Keeps roles reusable outside collection
- Clear documentation of collection vs role variables

### Documentation

1. **Include README** in collection root with:
   - Purpose of collection
   - Link to license file
   - General usage info (supported ansible-core versions, required libraries)
2. **Generate plugin documentation** from code (use `ansible-network/collection_prep`)
3. **Supplemental docs** in `docs/docsite/rst/`

### License

1. **Include LICENSE or COPYING** in root directory
2. **Note different licenses** in file headers if applicable

## Plugins Best Practices

### Python Guidelines

1. Use PEP8
2. Add file headers and function comments
3. Use sphinx (reST) formatted docstrings:
   ```python
   """[Summary]

   :param [ParamName]: [ParamDescription], defaults to [DefaultParamVal]
   :type [ParamName]: [ParamType](, optional)
   :raises [ErrorType]: [ErrorDescription]
   :return: [ReturnDescription]
   :rtype: [ReturnType]
   """
   ```
4. Use Python type hints (Python 3.5+)
5. Use pytest for unit tests, not unittest

### Documentation

1. **Document all plugin types** - input parameters, outputs, examples
2. Follow Ansible Developer Guide standards

### Code Organization

1. **Keep entry files minimal** - move reusable code to `module_utils/` or `plugin_utils/`
2. **Use `ansible.plugin_builder`** for scaffolding new plugins
3. **Maintain consistent argspec formatting** within collection

### Error/Info Messages

1. **Use clear, specific error messages** - not "Failed!"
2. **Use AnsibleModule helper methods**: `fail_json()`, `warn()`, `deprecate()`
3. **Use Display class** for verbosity-based output:
   ```python
   from ansible.utils.display import Display
   display = Display()
   display.vvvv("Debug info at high verbosity")
   ```

### Example Error Handling

```python
# Module failure with details
if checksum and checksum_src != checksum:
    module.fail_json(
        msg='Copied file does not match the expected checksum.',
        checksum=checksum_src,
        expected_checksum=checksum
    )

# Warning without exit
module.warn('Permission denied fetching key metadata ({0})'.format(key_id))

# Deprecation notice
module.deprecate(
    "Option deprecated, use new_option instead",
    version="3.0.0",
    collection_name='community.general'
)
```

## Quick Reference Checklist

When writing Ansible code, verify:

- [ ] All variables prefixed with role name
- [ ] Internal variables use `__` prefix
- [ ] Tasks are idempotent
- [ ] Check mode supported
- [ ] Task names are descriptive and imperative
- [ ] Using `true`/`false` for booleans
- [ ] Using `.yml` extension
- [ ] Using YAML style for task arguments
- [ ] Long lines wrapped appropriately
- [ ] Using bracket notation for variables: `var['key']`
- [ ] Using `| bool` filter with bare variables in `when`
- [ ] Not using `command`/`shell` without justification
- [ ] Not using `set_fact` to override role vars
- [ ] Templates have `.j2` extension
- [ ] Templates have `{{ ansible_managed | comment }}` header
- [ ] Platform-specific vars in `vars/` files, not in tasks
- [ ] Role has `meta/argument_specs.yml` if Ansible 2.11+
- [ ] README documents all input/output variables
- [ ] Using semantic versioning for releases

---

**Remember**: These are *good* practices, not *best* practices. Apply them where they make sense for your specific use case and organization. The goal is maintainability, readability, and reusability - not blind adherence to rules.
