# Instructions for AI agents

Analyze and propose updates to `../docs/agents.md` file to ensure that it
contains the following

## TOC

Keep the current TOC structure below on the generated document but feel free
to add other sections if needed:

- Guiding Principles
- Development Workflow
  - Project structure
    - Collection project
    - Playbook project
  - Version Control
  - Starting Approach
  - Testing and Validation
    - Testing Strategies
    - Smoke Testing
- Coding Standards
  - Formatting
    - YAML Formatting
    - Python Formatting
    - Markdown Formatting
  - Ansible specific
    - Naming Conventions
      - General Naming Rules
      - Variable Naming
      - Task Naming
      - Role-Specific Naming
    - Collections
    - Roles
    - Inventories and Variables
    - Plugins and modules
    - Playbooks
      - Structure and Simplicity
      - Tags
      - Debug and Output
      - Waiting for Conditions
  - Python code
  - Jinja2 Templates
  - Other files
    - Line Wrapping
- Glossary

## Preparatory information

- When creating references try to avoid "see" sections if you can just use markdown hyperlinks inside the text.
- Use inline markdown code blocks (backticks) when mentioning keywords or commands that are to be executed.
- After you modify files run `pre-commit` and include changes it makes and fix reported problems if any until it passes.

Best practices suggest only two project layout structures:

### Playbook project (with adjacent collection)

A playbook project orchestrates landscapes and types via one or more playbooks, with all role and plugin authoring done in an adjacent in-repo collection kept local until it's mature enough to become a standalone collection. Typical layout includes per‑environment inventories, a playbooks/ directory, and collections/ansible_collections/<namespace>/<name>/ for the adjacent collection; scaffold with ansible-creator init playbook and add roles/plugins with ansible-creator add. It emphasizes data‑driven inputs (SSOT, clear As‑Is vs To‑Be, inventory vars over extra vars), strict style/lint alignment (FQCNs, explicit state, loop over with_), and idempotent, check‑mode‑safe content. Pin an Execution Environment, declare a supported OS/ansible‑core matrix, and enforce CI (ansible‑lint + Molecule for roles with an idempotence rerun). Use when you need purpose‑built orchestration with tightly scoped, reusable roles that don't yet need external distribution.

### Collection project (packaged & reusable)

A collection project packages reusable roles, plugins, and docs for distribution (private hub or Galaxy), with a standard structure (galaxy.yml, roles/, plugins/, meta/, tests/, docs/); scaffold with ansible-creator init collection and extend via ansible-creator add. Authoring focuses on clear public interfaces (argument_specs), provider abstraction, platform‑specific vars loading, naming conventions, and rigorous lint/style conformance. It requires deterministic builds (pin EE, collections, Python deps), CI with ansible‑lint and Molecule across a declared support matrix, and semantic versioning with CHANGELOG for safe upgrades. Use when you need shareable, versioned automation building blocks that multiple teams/environments can consume consistently.

### Instructions for Project structure section

When generating the "Project structure" section in the output document:

- [ ] Focus on key distinguishing characteristics between project types (directory layout, scaffolding commands, when to use each)
- [ ] Do NOT duplicate rules that are covered in detail in other sections
- [ ] Replace mentions of concepts with cross-references to their dedicated sections using markdown links
- [ ] Concepts that should be cross-referenced (not duplicated): naming conventions, SSOT, As-Is vs To-Be, FQCNs, inventory vars vs extra vars, idempotency, check mode, linting, testing strategies, semantic versioning, etc.
- [ ] Keep bullets focused on project-structure-specific guidance (scaffolding commands, directory organization, when to use each type)
- [ ] Embed markdown hyperlinks naturally in the text instead of using "see [Section]" format. Example: "Follow [naming conventions](#naming-conventions)" instead of "Follow naming conventions (see [Naming Conventions](#naming-conventions))"

## Analyze information

- [ ] Ansible best practices described inside the sources below:
  - `.` project (ansible-creator)
  - `../../automation-good-practices/**/*.adoc`
  - `../../ansible-lint/docs/rules/*.md`
  - `../../ansible-risk-insight/docs/rules/*.md`
  - blog post from https://www.ansiblejunky.com/blog/ansible-101-standards/
  - ansible core documentation from https://docs.ansible.com/ansible-core/devel/index.html
- [ ] Avoid using emoji in the generated file
- [ ] Itemize generated rules as todo lists with the exception on Zen of Ansible ones for which a normal bullet list should be used.
- [ ] Do not include code examples but if the text description of the rule is not clear enough try to improve it
- [ ] Ensure that the document has a glossary of terms at the end that includes
  at least definitions for the items below:
  - full qualified collection name (FQCN)
  - CMDB
  - SSOT
- [ ] Put rules affecting roles under their own section, same for collection related rules
- [ ] Ensure there is a section for formatting that has subsections for different
  file types such: YAML, python, markdown.
- [ ] For python files mention that `ruff format` should pass without making more changes
- [ ] For python files do not mention use of PEP8 but mention that running `ruff` should return no errors
- [ ] For python files mention that running `mypy .` should return no problems
- [ ] Include a TOC at the beginning of the document
- [ ] Add a top section name Coding standards that should include Collections, Roles, Inventories and Variables, Plugins, Python in this order. Ansible lint rules should not be under an ansible-lint section and instead they should be moved to other sections based on each rule nature.
- [ ] For python docstrings do not mention use of sphinx formatting but mention that running `pydoclint` should pass
