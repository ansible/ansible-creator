"""Unit tests for ansible-creator execution environment config dataclasses and schemas."""

from __future__ import annotations

import argparse

import pytest

from ansible_creator.exceptions import CreatorError
from ansible_creator.schema import _extract_action_info, for_command
from ansible_creator.types import EECollection, EEConfig, GalaxyServer, ScmServer


def test_ee_config_from_dict_full() -> None:
    """Test EEConfig.from_dict with all supported fields."""
    data = {
        "ee_name": "my-ee",
        "base_image": "quay.io/custom:latest",
        "collections": [{"name": "ansible.posix", "version": ">=1.0"}],
        "python_deps": ["jmespath"],
        "system_packages": ["git"],
        "additional_build_files": [{"src": "a.cfg", "dest": "configs"}],
        "additional_build_steps": {"prepend_base": ["RUN echo hi"]},
        "options": {"package_manager_path": "/usr/bin/dnf"},
        "ansible_cfg": "[galaxy]\nserver_list = hub\n",
        "build_arg_defaults": {"ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": "--pre"},
    }
    cfg = EEConfig.from_dict(data)

    assert cfg.ee_name == "my-ee"
    assert cfg.base_image == "quay.io/custom:latest"
    assert len(cfg.collections) == 1
    assert cfg.collections[0].name == "ansible.posix"
    assert cfg.collections[0].version == ">=1.0"
    assert cfg.python_deps == ("jmespath",)
    assert cfg.system_packages == ("git",)
    assert cfg.additional_build_files == ({"src": "a.cfg", "dest": "configs"},)
    assert cfg.additional_build_steps == {"prepend_base": ["RUN echo hi"]}
    assert cfg.options == {"package_manager_path": "/usr/bin/dnf"}
    assert cfg.build_arg_defaults == {"ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": "--pre"}
    assert "server_list" in cfg.ansible_cfg
    assert not cfg.galaxy_servers


def test_ee_config_from_dict_galaxy_servers() -> None:
    """Test EEConfig.from_dict with galaxy_servers list."""
    data = {
        "galaxy_servers": [
            {
                "id": "automation_hub",
                "url": "https://console.redhat.com/api/automation-hub/content/published/",
                "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
                "token_required": True,
            },
            {
                "id": "private_hub",
                "url": "https://pah.corp.example.com/api/galaxy/content/published/",
                "token_required": True,
                "validate_certs": False,
            },
            {
                "id": "galaxy",
                "url": "https://galaxy.ansible.com/",
            },
        ],
    }
    cfg = EEConfig.from_dict(data)

    assert len(cfg.galaxy_servers) == 3  # noqa: PLR2004
    assert cfg.galaxy_servers[0].id == "automation_hub"
    assert "console.redhat.com" in cfg.galaxy_servers[0].url
    assert "sso.redhat.com" in cfg.galaxy_servers[0].auth_url
    assert cfg.galaxy_servers[0].token_required is True
    assert cfg.galaxy_servers[0].validate_certs is True
    assert cfg.galaxy_servers[1].id == "private_hub"
    assert cfg.galaxy_servers[1].token_required is True
    assert cfg.galaxy_servers[1].validate_certs is False
    assert cfg.galaxy_servers[2].id == "galaxy"
    assert cfg.galaxy_servers[2].token_required is False
    assert cfg.galaxy_servers[2].validate_certs is True


def test_ee_config_from_dict_registry_and_image_name() -> None:
    """Test EEConfig.from_dict with registry and image_name."""
    cfg = EEConfig.from_dict({"registry": "quay.io", "image_name": "my-org/my-ee"})
    assert cfg.registry == "quay.io"
    assert cfg.image_name == "my-org/my-ee"

    cfg_default = EEConfig.from_dict({})
    assert cfg_default.registry == "ghcr.io"
    assert cfg_default.image_name == ""


def test_ee_config_from_dict_registry_rejects_url() -> None:
    """Test EEConfig.from_dict rejects registry with URL scheme."""
    with pytest.raises(CreatorError, match="Invalid registry"):
        EEConfig.from_dict({"registry": "https://ghcr.io"})

    with pytest.raises(CreatorError, match="Invalid registry"):
        EEConfig.from_dict({"registry": "http://quay.io"})


def test_ee_config_from_dict_ee_file_name() -> None:
    """Test EEConfig.from_dict with custom ee_file_name."""
    cfg = EEConfig.from_dict({"ee_file_name": "my-ee.yml"})
    assert cfg.ee_file_name == "my-ee.yml"

    cfg_yaml = EEConfig.from_dict({"ee_file_name": "custom.yaml"})
    assert cfg_yaml.ee_file_name == "custom.yaml"

    cfg_default = EEConfig.from_dict({})
    assert cfg_default.ee_file_name == "execution-environment.yml"


def test_ee_config_ee_file_name_validation() -> None:
    """Test that ee_file_name rejects paths and non-YAML extensions."""
    with pytest.raises(ValueError, match="plain filename"):
        EEConfig.from_dict({"ee_file_name": "../etc/evil.yml"})

    with pytest.raises(ValueError, match="plain filename"):
        EEConfig.from_dict({"ee_file_name": "sub/dir/ee.yml"})

    with pytest.raises(ValueError, match="plain filename"):
        EEConfig.from_dict({"ee_file_name": "sub\\dir\\ee.yml"})

    with pytest.raises(ValueError, match=r"\.yml or \.yaml"):
        EEConfig.from_dict({"ee_file_name": "ee-def.json"})

    with pytest.raises(ValueError, match=r"\.yml or \.yaml"):
        EEConfig.from_dict({"ee_file_name": "ee-def.txt"})


def test_ee_config_from_dict_defaults() -> None:
    """Test EEConfig.from_dict with empty dict uses defaults."""
    cfg = EEConfig.from_dict({})

    assert cfg.ee_name == "ansible_sample_ee"
    assert cfg.base_image == "quay.io/fedora/fedora:41"
    assert cfg.registry == "ghcr.io"
    assert cfg.image_name == ""
    assert not cfg.collections
    assert not cfg.python_deps
    assert not cfg.galaxy_servers
    assert not cfg.scm_servers
    assert not cfg.build_arg_defaults


def test_ee_config_from_dict_build_arg_defaults_invalid() -> None:
    """Test EEConfig.from_dict rejects non-string build_arg_defaults values."""
    with pytest.raises(CreatorError, match="build_arg_defaults"):
        EEConfig.from_dict({"build_arg_defaults": "not-a-mapping"})

    with pytest.raises(CreatorError, match="build_arg_defaults"):
        EEConfig.from_dict({"build_arg_defaults": {"FOO": 1}})


def test_ee_collection_from_dict_invalid_name() -> None:
    """Test EECollection.from_dict rejects invalid collection names."""
    with pytest.raises(CreatorError, match="Invalid collection name"):
        EECollection.from_dict({"name": "bad-name"})


def test_ee_collection_as_dict_sparse() -> None:
    """Test EECollection.as_dict only includes non-empty fields."""
    col = EECollection(name="ansible.posix")
    assert col.as_dict() == {"name": "ansible.posix"}

    col_full = EECollection(name="ansible.posix", version="1.0", type="galaxy")
    result = col_full.as_dict()
    assert result == {"name": "ansible.posix", "version": "1.0", "type": "galaxy"}


def test_ee_config_from_dict_rejects_unknown_keys() -> None:
    """Test EEConfig.from_dict rejects unknown keys."""
    with pytest.raises(CreatorError, match=r"Unknown key.*EE config.*bogus"):
        EEConfig.from_dict({"bogus": "value"})

    with pytest.raises(CreatorError, match=r"Unknown key.*EE config.*collection_list"):
        EEConfig.from_dict({"base_image": "quay.io/test:1", "collection_list": []})

    with pytest.raises(CreatorError, match=r"Unknown key.*EE config.*base_images"):
        EEConfig.from_dict({"base_images": "quay.io/test:1"})


def test_ee_collection_from_dict_rejects_unknown_keys() -> None:
    """Test EECollection.from_dict rejects unknown keys."""
    with pytest.raises(CreatorError, match=r"Unknown key.*collection.*src"):
        EECollection.from_dict({"name": "ansible.posix", "src": "foo"})

    with pytest.raises(CreatorError, match=r"Unknown key.*collection.*extra"):
        EECollection.from_dict({"name": "ansible.posix", "extra": "bar"})


def test_ee_config_to_schema_shape() -> None:
    """Test EEConfig.to_schema returns expected structure."""
    schema = EEConfig.to_schema()

    assert schema["type"] == "object"
    props = schema["properties"]
    assert "ee_name" in props
    assert "base_image" in props
    assert "collections" in props
    assert props["collections"]["type"] == "array"
    assert props["collections"]["items"]["type"] == "object"
    assert "name" in props["collections"]["items"]["properties"]
    assert "python_deps" in props
    assert "system_packages" in props
    assert "ansible_cfg" in props
    assert "registry" in props
    assert "image_name" in props
    assert "galaxy_servers" in props
    assert props["galaxy_servers"]["type"] == "array"
    assert "scm_servers" in props
    assert props["scm_servers"]["type"] == "array"
    assert "ee_file_name" in props
    assert "build_arg_defaults" in props


def test_ee_config_schema_in_cli_schema() -> None:
    """Test that the CLI schema exposes EEConfig structure for ee_config."""
    schema = for_command("init", "execution_env")
    ee_config_schema = schema["parameters"]["properties"]["ee_config"]

    assert ee_config_schema["type"] == "object"
    assert "properties" in ee_config_schema
    assert "ee_name" in ee_config_schema["properties"]
    assert "base_image" in ee_config_schema["properties"]
    assert "collections" in ee_config_schema["properties"]


def test_init_execution_env_scm_provider_schema() -> None:
    """CLI schema lists scm_provider for init execution_env."""
    schema = for_command("init", "execution_env")
    scm = schema["parameters"]["properties"]["scm_provider"]
    assert scm["enum"] == ["github", "gitlab"]
    assert scm["default"] == "github"


def test_extract_action_info_schema_class_no_option_strings() -> None:
    """Test _extract_action_info with schema_class but no option_strings."""
    action = argparse.Action(option_strings=[], dest="ee_config")
    action.help = "EE configuration"
    action.schema_class = EEConfig  # type: ignore[attr-defined]

    info = _extract_action_info(action)

    assert info["type"] == "object"
    assert info["description"] == "EE configuration"
    assert "aliases" not in info


def test_ee_collection_from_dict_git_url_formats() -> None:
    """Test that EECollection.from_dict accepts all Git URL formats."""
    git_urls = [
        "git://github.com/org/repo",
        "ssh://git@github.com/org/repo",
        "file:///local/path/to/collection",
        "git@github.com:org/repo.git",
        "https://github.com/org/repo",
    ]
    for url in git_urls:
        col = EECollection.from_dict({"name": url})
        assert col.name == url


def test_galaxy_server_from_dict_full() -> None:
    """Test GalaxyServer.from_dict with all fields."""
    data = {
        "id": "automation_hub",
        "url": "https://console.redhat.com/api/automation-hub/content/published/",
        "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        "token_required": True,
    }
    server = GalaxyServer.from_dict(data)

    assert server.id == "automation_hub"
    assert "console.redhat.com" in server.url
    assert "sso.redhat.com" in server.auth_url
    assert server.token_required is True
    assert server.validate_certs is True


def test_galaxy_server_from_dict_validate_certs_false() -> None:
    """Test GalaxyServer.from_dict with validate_certs false."""
    server = GalaxyServer.from_dict(
        {
            "id": "internal_hub",
            "url": "https://10.0.0.1/api/galaxy/content/published/",
            "validate_certs": False,
        },
    )
    assert server.id == "internal_hub"
    assert server.validate_certs is False


def test_galaxy_server_from_dict_minimal() -> None:
    """Test GalaxyServer.from_dict with only required fields."""
    server = GalaxyServer.from_dict({"id": "galaxy", "url": "https://galaxy.ansible.com/"})

    assert server.id == "galaxy"
    assert server.url == "https://galaxy.ansible.com/"
    assert server.auth_url == ""
    assert server.token_required is False
    assert server.validate_certs is True


def test_galaxy_server_from_dict_missing_id() -> None:
    """Test GalaxyServer.from_dict rejects missing id."""
    with pytest.raises(CreatorError, match="must have an 'id' field"):
        GalaxyServer.from_dict({"url": "https://galaxy.ansible.com/"})


def test_galaxy_server_from_dict_missing_url() -> None:
    """Test GalaxyServer.from_dict rejects missing url."""
    with pytest.raises(CreatorError, match="must have a 'url' field"):
        GalaxyServer.from_dict({"id": "galaxy"})


def test_galaxy_server_from_dict_invalid_id() -> None:
    """Test GalaxyServer.from_dict rejects invalid server IDs."""
    with pytest.raises(CreatorError, match="Invalid galaxy server id"):
        GalaxyServer.from_dict({"id": "Bad-Id", "url": "https://example.com/"})

    with pytest.raises(CreatorError, match="Invalid galaxy server id"):
        GalaxyServer.from_dict({"id": "has.dot", "url": "https://example.com/"})


def test_galaxy_server_as_dict() -> None:
    """Test GalaxyServer.as_dict includes derived token_env_var."""
    server = GalaxyServer(
        id="automation_hub",
        url="https://example.com/",
        auth_url="https://sso.example.com/token",
        token_required=True,
        validate_certs=True,
    )
    result = server.as_dict()

    assert result["id"] == "automation_hub"
    assert result["url"] == "https://example.com/"
    assert result["auth_url"] == "https://sso.example.com/token"
    assert result["token_required"] is True
    assert result["validate_certs"] is True
    expected_var = "ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN"
    assert result["token_env_var"] == expected_var


def test_galaxy_server_as_dict_no_auth_url() -> None:
    """Test GalaxyServer.as_dict omits auth_url when empty."""
    server = GalaxyServer(id="galaxy", url="https://galaxy.ansible.com/")
    result = server.as_dict()

    assert "auth_url" not in result
    assert result["validate_certs"] is True
    expected_var = "ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN"
    assert result["token_env_var"] == expected_var


def test_galaxy_server_to_schema() -> None:
    """Test GalaxyServer.to_schema returns expected structure."""
    schema = GalaxyServer.to_schema()

    assert schema["type"] == "object"
    assert "id" in schema["required"]
    assert "url" in schema["required"]
    props = schema["properties"]
    assert "id" in props
    assert "url" in props
    assert "auth_url" in props
    assert "token_required" in props
    assert "validate_certs" in props


def test_scm_server_from_dict_full() -> None:
    """Test ScmServer.from_dict with all fields."""
    data = {
        "id": "github_org1",
        "hostname": "github.com",
        "token_env_var": "GITHUB_ORG1_TOKEN",
    }
    server = ScmServer.from_dict(data)

    assert server.id == "github_org1"
    assert server.hostname == "github.com"
    assert server.token_env_var == "GITHUB_ORG1_TOKEN"  # noqa: S105


def test_scm_server_from_dict_missing_id() -> None:
    """Test ScmServer.from_dict rejects missing id."""
    with pytest.raises(CreatorError, match="must have an 'id' field"):
        ScmServer.from_dict({"hostname": "github.com", "token_env_var": "TOKEN"})


def test_scm_server_from_dict_missing_hostname() -> None:
    """Test ScmServer.from_dict rejects missing hostname."""
    with pytest.raises(CreatorError, match="must have a 'hostname' field"):
        ScmServer.from_dict({"id": "github", "token_env_var": "TOKEN"})


def test_scm_server_from_dict_missing_token_env_var() -> None:
    """Test ScmServer.from_dict rejects missing token_env_var."""
    with pytest.raises(CreatorError, match="must have a 'token_env_var' field"):
        ScmServer.from_dict({"id": "github", "hostname": "github.com"})


def test_scm_server_from_dict_invalid_id() -> None:
    """Test ScmServer.from_dict rejects invalid server IDs."""
    with pytest.raises(CreatorError, match="Invalid SCM server id"):
        ScmServer.from_dict(
            {
                "id": "Bad-Id",
                "hostname": "github.com",
                "token_env_var": "TOKEN",
            }
        )


def test_scm_server_from_dict_invalid_token_env_var() -> None:
    """Test ScmServer.from_dict rejects invalid environment variable names."""
    with pytest.raises(CreatorError, match="Invalid token_env_var"):
        ScmServer.from_dict(
            {
                "id": "github",
                "hostname": "github.com",
                "token_env_var": "lowercase_bad",
            }
        )

    with pytest.raises(CreatorError, match="Invalid token_env_var"):
        ScmServer.from_dict(
            {
                "id": "github",
                "hostname": "github.com",
                "token_env_var": "HAS-DASHES",
            }
        )

    with pytest.raises(CreatorError, match="Invalid token_env_var"):
        ScmServer.from_dict(
            {
                "id": "github",
                "hostname": "github.com",
                "token_env_var": "123_STARTS_WITH_DIGIT",
            }
        )


def test_scm_server_as_dict() -> None:
    """Test ScmServer.as_dict returns all fields."""
    server = ScmServer(
        id="internal_gitlab",
        hostname="gitlab.corp.com",
        token_env_var="INTERNAL_GITLAB_TOKEN",  # noqa: S106
    )
    result = server.as_dict()

    assert result["id"] == "internal_gitlab"
    assert result["hostname"] == "gitlab.corp.com"
    expected_var = "INTERNAL_GITLAB_TOKEN"
    assert result["token_env_var"] == expected_var


def test_scm_server_to_schema() -> None:
    """Test ScmServer.to_schema returns expected structure."""
    schema = ScmServer.to_schema()

    assert schema["type"] == "object"
    assert "id" in schema["required"]
    assert "hostname" in schema["required"]
    assert "token_env_var" in schema["required"]
    props = schema["properties"]
    assert "id" in props
    assert "hostname" in props
    assert "token_env_var" in props


def test_scm_server_to_schema_validation_metadata() -> None:
    """Test ScmServer.to_schema includes validation constraints."""
    schema = ScmServer.to_schema()
    props = schema["properties"]
    assert props["id"]["pattern"] == r"^[a-z_][a-z0-9_]*$"
    assert props["id"]["minLength"] == 1
    assert props["hostname"]["minLength"] == 1
    assert props["token_env_var"]["pattern"] == r"^[A-Z][A-Z0-9_]*$"
    assert props["token_env_var"]["minLength"] == 1


def test_galaxy_server_to_schema_validation_metadata() -> None:
    """Test GalaxyServer.to_schema includes validation constraints."""
    schema = GalaxyServer.to_schema()
    props = schema["properties"]
    assert props["id"]["pattern"] == r"^[a-z_][a-z0-9_]*$"
    assert props["id"]["minLength"] == 1
    assert props["url"]["format"] == "url"
    assert props["url"]["minLength"] == 1
    assert props["auth_url"]["format"] == "url"


def test_ee_collection_to_schema_validation_metadata() -> None:
    """Test EECollection.to_schema includes validation constraints."""
    schema = EECollection.to_schema()
    props = schema["properties"]
    assert props["name"]["minLength"] == 1
    assert props["source"]["format"] == "url"


def test_ee_config_to_schema_validation_metadata() -> None:
    """Test EEConfig.to_schema includes validation constraints."""
    schema = EEConfig.to_schema()
    props = schema["properties"]
    assert props["ee_name"]["minLength"] == 1
    assert props["base_image"]["minLength"] == 1
    assert props["registry"]["minLength"] == 1
    assert props["collections"]["minItems"] == 0
    assert props["python_deps"]["items"]["minLength"] == 1
    assert props["system_packages"]["items"]["minLength"] == 1
    assert props["ee_file_name"]["pattern"] == r"^[^/\\]*\.(yml|yaml)$"
    expected_ee_file_min_len = 5
    assert props["ee_file_name"]["minLength"] == expected_ee_file_min_len


def test_ee_config_from_dict_scm_servers() -> None:
    """Test EEConfig.from_dict parses scm_servers list."""
    data = {
        "scm_servers": [
            {
                "id": "github_org1",
                "hostname": "github.com",
                "token_env_var": "GITHUB_ORG1_TOKEN",
            },
            {
                "id": "internal_gitlab",
                "hostname": "gitlab.corp.com",
                "token_env_var": "INTERNAL_GITLAB_TOKEN",
            },
        ],
    }
    cfg = EEConfig.from_dict(data)

    assert len(cfg.scm_servers) == 2  # noqa: PLR2004
    assert cfg.scm_servers[0].id == "github_org1"
    assert cfg.scm_servers[0].hostname == "github.com"
    assert cfg.scm_servers[0].token_env_var == "GITHUB_ORG1_TOKEN"  # noqa: S105
    assert cfg.scm_servers[1].id == "internal_gitlab"
