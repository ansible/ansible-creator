"""Definitions for ansible-creator migrate action."""

from __future__ import annotations

import re
import shutil

from importlib import resources as impl_resources
from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.types import TemplateData
from ansible_creator.utils import ask_yes_no, expand_path


if TYPE_CHECKING:
    from pathlib import Path

    from ansible_creator.config import Config
    from ansible_creator.output import Output

RESOURCE_PACKAGE = "ansible_creator.resources.common.molecule_migrate"
TASK_MAIN_NAMES = ("tasks/main.yml", "tasks/main.yaml")
META_MAIN_NAMES = ("meta/main.yml", "meta/main.yaml")
_ROLE_REF_RE = re.compile(r"role:\s*(\S+)")


class Migrate:
    """Class to handle the migrate subcommand."""

    def __init__(self, config: Config) -> None:
        """Initialize the migrate action.

        Args:
            config: App configuration object.
        """
        self._migrate_type: str = config.migrate_type
        self._target_name: str = config.target_name
        self._migrate_all: bool = config.migrate_all
        self._keep_targets: bool = config.keep_targets
        self._collection_path: Path = expand_path(str(config.path))
        self._force = config.force
        self._overwrite = config.overwrite
        self._no_overwrite = config.no_overwrite
        self._skip_collection_check = config.skip_collection_check
        self.output: Output = config.output
        self.templar = Templar()
        self._resource_root = impl_resources.files(RESOURCE_PACKAGE)

    def run(self) -> None:
        """Start the migration.

        Raises:
            CreatorError: If the migrate type is unsupported or migration fails.
        """
        if self._migrate_type != "molecule":
            msg = f"Unsupported migrate type: {self._migrate_type!r}. Choose from: molecule"
            raise CreatorError(msg)

        self._check_path_exists()
        self._check_collection_path()
        self._migrate_molecule()

    def _check_path_exists(self) -> None:
        """Validate the provided collection path.

        Raises:
            CreatorError: If the path does not exist.
        """
        if not self._collection_path.exists():
            msg = (
                f"The path {self._collection_path} does not exist. "
                "Please provide an existing directory."
            )
            raise CreatorError(msg)

    def _check_collection_path(self) -> None:
        """Validate that the path is an Ansible collection.

        Raises:
            CreatorError: If the path is not a collection path.
        """
        if self._skip_collection_check:
            return

        galaxy_file_path = self._collection_path / "galaxy.yml"
        if not galaxy_file_path.is_file():
            msg = (
                f"The path {self._collection_path} is not a valid Ansible collection path. "
                "Please provide the root path of a valid ansible collection."
            )
            raise CreatorError(msg)

    def _migrate_molecule(self) -> None:
        """Migrate ansible-test integration targets into Molecule scenarios.

        Raises:
            CreatorError: If arguments are invalid or no role-shaped targets migrate.
        """
        if self._migrate_all and self._target_name:
            msg = "Specify either a target name or --all, not both."
            raise CreatorError(msg)
        if not self._migrate_all and not self._target_name:
            msg = "Specify a target name or --all."
            raise CreatorError(msg)

        targets_dir = self._collection_path / "tests" / "integration" / "targets"
        if not targets_dir.is_dir():
            msg = f"No integration targets directory found at {targets_dir}."
            raise CreatorError(msg)

        if self._migrate_all:
            candidates = sorted(path.name for path in targets_dir.iterdir() if path.is_dir())
        else:
            candidates = [self._target_name]

        migrated: list[str] = []
        skipped: list[str] = []

        for name in candidates:
            source = targets_dir / name
            if not source.is_dir():
                msg = f"Integration target not found: {source}"
                raise CreatorError(msg)
            if not self._is_role_shaped(source):
                self.output.warning(
                    msg=(
                        f"Skipping {name!r}: not a role-shaped target "
                        f"(expected tasks/main.yml or tasks/main.yaml)."
                    ),
                )
                skipped.append(name)
                continue
            self._migrate_one_target(name=name, source=source)
            migrated.append(name)

        if not migrated:
            msg = "No role-shaped integration targets were migrated."
            raise CreatorError(msg)

        dep_map = self._scan_cross_dependencies(migrated)
        self._write_guidance_artifacts(migrated, dep_map)
        self._ensure_shared_config()
        action = "copied" if self._keep_targets else "moved"
        self.output.note(
            msg=(
                f"{action.capitalize()} {len(migrated)} integration target(s) into "
                f"extensions/molecule/: {', '.join(migrated)}. "
                "Next: open extensions/molecule/MIGRATE_NEXT_STEPS.md or invoke the "
                "molecule-migrate-finalize agent skill."
            ),
        )
        if skipped:
            self.output.warning(msg=f"Skipped non-role targets: {', '.join(skipped)}")
        if dep_map:
            self.output.warning(
                msg=(
                    "Cross-target role dependencies detected. These require human or "
                    "agent analysis to map into Molecule's shared-state lifecycle model. "
                    "See MIGRATE_NEXT_STEPS.md for details."
                ),
            )

    @staticmethod
    def _is_role_shaped(target_dir: Path) -> bool:
        """Return True when the target looks like an Ansible role.

        Args:
            target_dir: Path to an integration target directory.

        Returns:
            Whether the target has tasks/main.yml or tasks/main.yaml.
        """
        return any((target_dir / relative).is_file() for relative in TASK_MAIN_NAMES)

    def _migrate_one_target(self, name: str, source: Path) -> None:
        """Migrate a single integration target into a Molecule scenario.

        Args:
            name: Target / scenario name.
            source: Path to tests/integration/targets/<name>.

        Raises:
            CreatorError: On overwrite conflicts when not permitted.
        """
        scenario_dir = self._collection_path / "extensions" / "molecule" / name
        content_dir = scenario_dir / "roles" / "content"
        molecule_yml = scenario_dir / "molecule.yml"
        converge_yml = scenario_dir / "converge.yml"

        conflicts = [
            path
            for path in (scenario_dir, content_dir, molecule_yml, converge_yml)
            if path.exists()
        ]
        if conflicts:
            conflict_list = ", ".join(str(path) for path in conflicts)
            if self._no_overwrite:
                msg = (
                    f"The following path(s) already exist and --no-overwrite was set: "
                    f"{conflict_list}"
                )
                raise CreatorError(msg)
            if not (self._force or self._overwrite):
                question = (
                    f"Path(s) already exist for scenario {name!r}: {conflict_list}. Overwrite?"
                )
                if not ask_yes_no(question):
                    msg = (
                        f"The program aborted due to existing content for scenario {name!r}. "
                        "Re-run with --overwrite to continue."
                    )
                    raise CreatorError(msg)

            # Conflicts imply scenario_dir already exists (children cannot exist without it).
            shutil.rmtree(scenario_dir)

        scenario_dir.mkdir(parents=True, exist_ok=True)
        content_dir.parent.mkdir(parents=True, exist_ok=True)
        template_data = TemplateData(scenario_name=name, target_name=name)
        molecule_yml.write_text(
            self._render_template("molecule.yml.j2", template_data),
            encoding="utf-8",
        )
        converge_yml.write_text(
            self._render_template("converge.yml.j2", template_data),
            encoding="utf-8",
        )

        if self._keep_targets:
            shutil.copytree(source, content_dir)
        else:
            shutil.move(str(source), str(content_dir))

        self.output.debug(msg=f"Migrated integration target {name!r} to {scenario_dir}")

    def _render_template(self, filename: str, data: TemplateData) -> str:
        """Load and render a migrate template.

        Args:
            filename: Template filename under the molecule_migrate resource package.
            data: Template data.

        Returns:
            Rendered template content.
        """
        template = (self._resource_root / filename).read_text(encoding="utf-8")
        return self.templar.render_from_content(template=template, data=data)

    def _scan_cross_dependencies(
        self,
        migrated: list[str],
    ) -> dict[str, list[str]]:
        """Scan migrated scenarios for cross-target role dependencies.

        Looks at ``meta/main.yml`` in each migrated target's content role
        for ``role:`` references that name other targets.  These cannot be
        resolved automatically — they require human or agent analysis to
        map into Molecule's shared-state lifecycle.

        Args:
            migrated: Names of targets that were migrated.

        Returns:
            Mapping of target name to list of referenced role names found
            in its ``meta/main.yml``.  Empty when no cross-refs detected.
        """
        molecule_root = self._collection_path / "extensions" / "molecule"
        migrated_set = set(migrated)
        dep_map: dict[str, list[str]] = {}

        for name in migrated:
            content_dir = molecule_root / name / "roles" / "content"
            for meta_name in META_MAIN_NAMES:
                meta_file = content_dir / meta_name
                if not meta_file.is_file():
                    continue
                text = meta_file.read_text(encoding="utf-8")
                refs = [
                    m.group(1)
                    for m in _ROLE_REF_RE.finditer(text)
                    if m.group(1) in migrated_set and m.group(1) != name
                ]
                if refs:
                    dep_map[name] = refs
                    self.output.warning(
                        msg=(
                            f"Target {name!r} references role(s) {refs} via meta/main.yml. "
                            "These cross-target dependencies need analysis — see "
                            "MIGRATE_NEXT_STEPS.md and the molecule-migrate-finalize skill."
                        ),
                    )
        return dep_map

    def _write_guidance_artifacts(
        self,
        migrated: list[str],
        dep_map: dict[str, list[str]],
    ) -> None:
        """Write next-steps checklist and agent skill into the collection.

        Args:
            migrated: Names of targets migrated in this run.
            dep_map: Cross-target dependency map from _scan_cross_dependencies.
        """
        molecule_root = self._collection_path / "extensions" / "molecule"
        molecule_root.mkdir(parents=True, exist_ok=True)

        next_steps = molecule_root / "MIGRATE_NEXT_STEPS.md"
        dep_lines = ""
        if dep_map:
            dep_lines = "\n".join(
                f"- **{target}** depends on: {', '.join(deps)}"
                for target, deps in sorted(dep_map.items())
            )
        template_data = TemplateData(
            scenario_name=", ".join(migrated),
            target_name=", ".join(migrated),
            cross_dependencies=dep_lines,
        )
        new_content = self._render_template("MIGRATE_NEXT_STEPS.md.j2", template_data)
        if not next_steps.exists():
            next_steps.write_text(new_content, encoding="utf-8")
        elif self._no_overwrite:
            self.output.warning(
                msg=f"Skipped updating {next_steps} because --no-overwrite was set.",
            )
        else:
            next_steps.write_text(new_content, encoding="utf-8")

        skill_dest = (
            self._collection_path / ".agents" / "skills" / "molecule-migrate-finalize" / "SKILL.md"
        )
        skill_dest.parent.mkdir(parents=True, exist_ok=True)
        skill_content = (self._resource_root / "SKILL.md").read_text(encoding="utf-8")
        if not skill_dest.exists() or skill_dest.read_text(encoding="utf-8") != skill_content:
            if skill_dest.exists() and self._no_overwrite:
                self.output.warning(
                    msg=f"Skipped updating {skill_dest} because --no-overwrite was set.",
                )
            else:
                skill_dest.write_text(skill_content, encoding="utf-8")

    def _ensure_shared_config(self) -> None:
        """Write shared config, inventory, and default scenario if missing."""
        molecule_root = self._collection_path / "extensions" / "molecule"
        molecule_root.mkdir(parents=True, exist_ok=True)
        for filename in ("config.yml", "inventory.yml"):
            dest = molecule_root / filename
            if dest.exists():
                continue
            dest.write_text(
                (self._resource_root / filename).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        default_dir = molecule_root / "default"
        default_mol = default_dir / "molecule.yml"
        if not default_mol.exists():
            default_dir.mkdir(parents=True, exist_ok=True)
            default_mol.write_text(
                (self._resource_root / "default_molecule.yml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
