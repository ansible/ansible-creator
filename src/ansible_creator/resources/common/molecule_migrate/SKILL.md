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
- Shared ansible-native config: `extensions/molecule/config.yml` + `inventory.yml`
- Checklist: `extensions/molecule/MIGRATE_NEXT_STEPS.md`

## Steps

1. List migrated scenarios under `extensions/molecule/` (ignore `utils/`, `config.yml`, `inventory.yml`, and `MIGRATE_NEXT_STEPS.md`).
2. Confirm shared inventory (`ansible_connection: local` on localhost) matches how the old targets ran. Add scenario-local inventory only when a target needs something else; do not invent cloud creds.
3. Inspect `roles/content/` for ansible-test-only files (`aliases`, `runme.sh`, setup deps). Remove or document anything Molecule will not honor.
4. From the collection root, run `molecule test -s <target>` (or `molecule test --all` when appropriate). Fix playbook/role path issues first if converge fails to find role `content`.
5. Update CI/tox so integration for migrated targets invokes Molecule, not `ansible-test integration`.
6. Clean empty `tests/integration/targets/` dirs; note remaining script-shaped targets that were skipped.
7. Summarize what changed, what still needs human platform/CI decisions, and any scenarios that failed verification.
