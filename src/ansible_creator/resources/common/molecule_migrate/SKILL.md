---
name: molecule-migrate-finalize
description: >-
  Finalize a collection after ansible-creator migrate molecule moved
  tests/integration/targets into extensions/molecule scenarios. Use when the
  user says migrate finalize, post-migrate molecule, or after running
  ansible-creator migrate molecule.
---

# Finalize Molecule migration

Mechanical migration is done. Help the maintainer finish a safe, runnable Molecule layout.

## Context

- Scenarios: `extensions/molecule/<target>/`
- Role content: `extensions/molecule/<target>/roles/content/` (former ansible-test target)
- Shared config: `extensions/molecule/config.yml` — ansible-native executor, `shared_state: true`
- Inventory: `extensions/molecule/inventory.yml`
- Default scenario: `extensions/molecule/default/molecule.yml` — lifecycle manager (create/destroy)
- Checklist: `extensions/molecule/MIGRATE_NEXT_STEPS.md`

## Architecture: shared-state model

With `shared_state: true` in `config.yml`, Molecule delegates lifecycle management to the
`default` scenario.  The `default` scenario owns `create` → `prepare` → `destroy`, and
component scenarios only run `converge` → `verify`.  This mirrors the ansible-test model
where `setup_*` roles run before dependent targets.

Reference: <https://docs.ansible.com/projects/molecule/getting-started-collections/>

## Steps

1. Read `MIGRATE_NEXT_STEPS.md` for the list of migrated scenarios and any cross-target
   dependencies that were detected.

2. **Analyze cross-target dependencies.** For each dependency listed:
   - If the dependency role provides *shared infrastructure* (common packages, services,
     config), fold it into `default/prepare.yml`.
   - If the dependency is *scenario-specific preparation* (test data, fixture setup),
     add a `prepare.yml` to that scenario.
   - Remove the `meta/main.yml` (or `meta/main.yaml`) dependency entries from migrated
     `roles/content/` — the Molecule lifecycle replaces them.

3. **Split converge from verify.** ansible-test integration targets almost always mix state
   application and assertions in `tasks/main.yml`.  Molecule separates these into distinct
   lifecycle phases (`converge` vs `verify`).  For each migrated scenario:
   - Open `roles/content/tasks/main.yml` (and any included task files).
   - Identify assertion tasks: `assert`, `fail` with `when`, `stat` + register + assert,
     check-mode-only tasks, and any `block:` sections whose sole purpose is validation.
   - Move those tasks into a new `verify.yml` playbook at the scenario root.  This lets
     maintainers re-run `molecule verify -s <target>` without re-converging — faster
     iteration and proper alignment with Molecule's lifecycle.
   - If a target's tasks are tightly interleaved (assert after every action), use judgment:
     quick inline sanity checks can stay in converge, but the final state validation should
     be in verify.

4. Confirm shared inventory (`ansible_connection: local` on localhost) matches how the old
   targets ran.  Add scenario-local inventory only when a target needs something different.

5. Inspect `roles/content/` for ansible-test-only files (`aliases`, `runme.sh`, setup deps).
   Remove or document anything Molecule will not honor.

6. From the collection root, run `molecule test -s <target>` (or `molecule test --all`).
   Fix playbook/role path issues first if converge fails to find role `content`.

7. Update CI/tox so integration for migrated targets invokes Molecule, not
   `ansible-test integration`.

8. Clean empty `tests/integration/targets/` dirs; note remaining script-shaped targets that
   were skipped.

9. Summarize what changed, what still needs human platform/CI decisions, and any scenarios
   that failed verification.
