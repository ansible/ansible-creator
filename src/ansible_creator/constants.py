"""Definition of constants for this package."""

GLOBAL_TEMPLATE_VARS = {
    "DEV_CONTAINER_IMAGE": "ghcr.io/ansible/community-ansible-dev-tools:latest",
    "DEV_FILE_IMAGE": "ghcr.io/ansible/ansible-workspace-env-reference:latest",
}

# directory names that will be skipped in any resource
SKIP_DIRS = ("__pycache__",)
# file types that will be skipped in any resource
SKIP_FILES_TYPES = (".pyc",)
