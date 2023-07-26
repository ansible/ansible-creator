MessageColors = {
    "HEADER": "\033[94m",
    "OKGREEN": "\033[92m",
    "WARNING": "\033[93m",
    "FAIL": "\033[1;31m",
    "OK": "\033[95m",
    "ENDC": "\033[0m",
}

# Note: do not change the ordering
COLLECTION_SKEL_DIRS = [
    ".github/workflows",
    "changelogs/fragments",
    "docs",
    "meta",
    "plugins/action",
    "plugins/cliconf",
    "plugins/filter",
    "plugins/httpapi",
    "plugins/inventory",
    "plugins/modules",
    "plugins/module_utils",
    "plugins/plugin_utils",
    "plugins/terminal",
    "plugins/test",
    "tests/integration",
    "tests/sanity",
    "tests/units",
]

COLLECTION_SKEL_TEMPLATES = [
    ".github/workflows/test.yml.j2",
    "README.md.j2",
    "galaxy.yml.j2",
    ".isort.cfg.j2",
    ".pre-commit-config.yaml.j2",
    "LICENSE.j2",
    "pyproject.toml.j2",
    ".prettierignore.j2",
]
