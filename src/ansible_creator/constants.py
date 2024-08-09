"""Definition of constants for this package."""

from __future__ import annotations


GLOBAL_TEMPLATE_VARS = {
    "DEV_CONTAINER_IMAGE": "ghcr.io/ansible/community-ansible-dev-tools:latest",
    "DEV_FILE_IMAGE": "ghcr.io/ansible/ansible-workspace-env-reference:latest",
    "RECOMMENDED_EXTENSIONS": ["redhat.ansible", "redhat.vscode-redhat-account"],
}

MIN_COLLECTION_NAME_LEN = 2

# directory names that will be skipped in any resource
SKIP_DIRS = ("__pycache__",)
# file types that will be skipped in any resource
SKIP_FILES_TYPES = (".pyc",)
