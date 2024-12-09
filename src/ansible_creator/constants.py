"""Definition of constants for this package."""

from __future__ import annotations


GLOBAL_TEMPLATE_VARS = {
    # DEV_CONTAINER_IMAGE gets updated with the downstream image when the package
    # is installed using rpm
    # See: https://gitlab.cee.redhat.com/aap-cpaas/config/ansible-creator/-/blob/ansible-automation-platform-2.5/distgit/rpms/ansible-creator/ansible-creator.spec.in?ref_type=heads#L34
    "DEV_CONTAINER_IMAGE": "ghcr.io/ansible/community-ansible-dev-tools:latest",
    "DEV_CONTAINER_UPSTREAM_IMAGE": "ghcr.io/ansible/community-ansible-dev-tools:latest",
    "DEV_CONTAINER_DOWNSTREAM_IMAGE": (
        "registry.redhat.io/ansible-automation-platform-25/ansible-dev-tools-rhel8:latest"
    ),
    "DEV_FILE_IMAGE": "ghcr.io/ansible/ansible-workspace-env-reference:latest",
    "RECOMMENDED_EXTENSIONS": ["redhat.ansible", "redhat.vscode-redhat-account"],
    "EXECUTION_ENVIRONMENT_DEFAULT_IMAGE": "quay.io/fedora/fedora:41",
}

MIN_COLLECTION_NAME_LEN = 2

# directory names that will be skipped in any resource
SKIP_DIRS = ("__pycache__",)
# file types that will be skipped in any resource
SKIP_FILES_TYPES = (".pyc",)
