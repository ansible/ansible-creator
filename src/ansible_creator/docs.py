"""Generate or update collection documentation."""
import ast
import logging
import os
import re
import shutil
import sys
import tempfile

from functools import partial
from pathlib import Path
from typing import Optional

import yaml

from ansible.module_utils._text import to_text
from ansible.module_utils.common.collections import is_sequence
from ansible.module_utils.six import string_types
from ansible.plugins.loader import fragment_loader
from ansible.utils import plugin_docs
from ansible.utils.collection_loader._collection_finder import _AnsibleCollectionFinder
from jinja2 import Environment
from jinja2 import FileSystemLoader

from ansible_creator.jinja_utils import documented_type
from ansible_creator.jinja_utils import from_kludge_ns
from ansible_creator.jinja_utils import html_ify
from ansible_creator.jinja_utils import rst_ify
from ansible_creator.jinja_utils import to_kludge_ns


logging.basicConfig(format="%(levelname)-10s%(message)s", level=logging.INFO)


IGNORE_FILES = ["__init__.py"]
SUBDIRS = (
    "become",
    "cliconf",
    "connection",
    "filter",
    "httpapi",
    "inventory",
    "lookup",
    "netconf",
    "modules",
    "test",
    "validate",
)
TEMPLATE_DIR = os.path.dirname(__file__)
ANSIBLE_COMPAT = """## Ansible version compatibility

This collection has been tested against following Ansible versions: **{requires_ansible}**.

For collections that support Ansible 2.9, please ensure you update your `network_os` to use the
fully qualified collection name (for example, `cisco.ios.ios`).
Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
"""


def ensure_list(value):
    """Ensure the value is a list.

    :param value: The value to check
    :type value: Unknown
    :return: The value as a list
    """
    if isinstance(value, list):
        return value
    return [value]


def convert_descriptions(data):
    """Convert the descriptions for doc into lists.

    :param data: the chunk from the doc
    :type data: dict
    """
    if data:
        for definition in data.values():
            if "description" in definition:
                definition["description"] = ensure_list(definition["description"])
            if "suboptions" in definition:
                convert_descriptions(definition["suboptions"])
            if "contains" in definition:
                convert_descriptions(definition["contains"])


def jinja_environment():
    """Define the jinja environment.

    :return: A jinja template, with the env set
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        variable_start_string="@{",
        variable_end_string="}@",
        lstrip_blocks=True,
        trim_blocks=True,
    )
    env.filters["rst_ify"] = rst_ify
    env.filters["documented_type"] = documented_type
    env.tests["list"] = partial(is_sequence, include_strings=False)
    env.filters["html_ify"] = html_ify
    env.globals["to_kludge_ns"] = to_kludge_ns
    env.globals["from_kludge_ns"] = from_kludge_ns
    template = env.get_template("plugin.rst.j2")
    return template


def update_readme(content, path, gh_url, branch_name):  # pylint: disable-msg=too-many-locals
    """Update the README.md in the repository.

    :param content: The dict containing the content
    :type content: dict
    :param path: The path to the collection
    :type path: str
    :param gh_url: The url to the GitHub repository
    :type gh_url: str
    :param branch_name: The name of the main repository branch
    :type branch_name: str
    """
    data = []
    gh_url = re.sub(r"\.git$", "", gh_url)
    for plugin_type, plugins in content.items():
        logging.info("Processing '%s' for README", plugin_type)
        if not plugins:
            continue
        if plugin_type == "modules":
            data.append("### Modules")
        else:
            data.append(f"### {plugin_type.capitalize()} plugins")
            if "_description" in plugins:
                data.append(plugins.pop("_description"))
                data.append("")
        data.append("Name | Description")
        data.append("--- | ---")
        for plugin, info in sorted(plugins.items()):
            if info["has_rst"]:
                link = (
                    f"[{plugin}]({gh_url}/blob/{branch_name}/docs/{plugin}_"
                    f"{plugin_type.replace('modules', 'module')}.rst)"
                )
            else:
                link = plugin
            description = info["comment"].replace("|", "\\|").strip()
            data.append(f"{link}|{description}")
        data.append("")
    readme = os.path.join(path, "README.md")
    try:
        with open(readme, encoding="utf8") as readme_file:
            content = readme_file.read().splitlines()
    except FileNotFoundError:
        logging.error("README.md not found in %s", path)
        logging.error("README.md not updated")
        sys.exit(1)
    try:
        start = content.index("<!--start collection content-->")
        end = content.index("<!--end collection content-->")
    except ValueError:
        logging.error("Content anchors not found in %s", readme)
        logging.error("README.md not updated")
        sys.exit(1)
    if start and end:
        new = content[0 : start + 1] + data + content[end:]
        with open(readme, "w", encoding="utf8") as readme_file:
            readme_file.write("\n".join(new))
            # Avoid "No newline at end of file.
            # No, I don't know why it has to be two of them.
            # Yes, it actually does have to be two of them.
            readme_file.write("\n\n")
        logging.info("README.md updated")


def handle_simple(collection, fullpath, kind):  # pylint: disable-msg=too-many-locals
    """Process "simple" plugins like filter or test.

    :param collection: The full collection name
    :type collection: str
    :param fullpath: The full path to the filter plugin file
    :type fullpath: str
    :param kind: The kind of plugin, filter or test
    :type kind: str
    :return: A dict of plugins + descriptions
    """
    if kind == "filter":
        class_name = "FilterModule"
        map_name = "filter_map"
        func_name = "filters"
    elif kind == "test":
        class_name = "TestModule"
        map_name = "test_map"
        func_name = "tests"
    else:
        logging.error("Only filter and test are supported simple types")
        sys.exit(1)

    plugins = {}
    with open(fullpath, encoding="utf8") as file_obj:
        file_contents = file_obj.read()
    module = ast.parse(file_contents)
    function_definitions = {
        node.name: ast.get_docstring(node)
        for node in module.body
        if isinstance(node, ast.FunctionDef)
    }
    class_def = [
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    ]
    if not class_def:
        return plugins

    docstring = ast.get_docstring(class_def[0], clean=True)
    if docstring:
        plugins["_description"] = docstring.strip()

    simple_map = next(
        (
            node
            for node in class_def[0].body
            if isinstance(node, ast.Assign)
            and hasattr(node, "targets")
            and node.targets[0].id == map_name
        ),
        None,
    )

    if not simple_map:
        simple_func = [
            func
            for func in class_def[0].body
            if isinstance(func, ast.FunctionDef) and func.name == func_name
        ]
        if not simple_func:
            return plugins

        # The filter map is either looked up using the filter_map = {}
        # assignment or if return returns a dict literal.
        simple_map = next(
            (
                node
                for node in simple_func[0].body
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
            ),
            None,
        )

    if not simple_map:
        return plugins

    keys = [k.s for k in simple_map.value.keys]
    logging.info("Adding %s plugins %s", kind, ",".join(keys))
    values = [k.id for k in simple_map.value.values]
    simple_map = dict(zip(keys, values))
    for name, func in simple_map.items():
        if func in function_definitions:
            comment = function_definitions[func] or f"{collection} {name} {kind} plugin"

            # Get the first line from the docstring for the description and
            # make that the short description.
            comment = next(c for c in comment.splitlines() if c and not c.startswith(":"))
            plugins[f"{collection}.{name}"] = {"has_rst": False, "comment": comment}
    return plugins


def process(collection: str, path: Path):  # pylint: disable-msg=too-many-locals,too-many-branches
    """Process the files in each subdirectory.

    :param collection: The collection name
    :type collection: str
    :param path: The path to the collection
    :type path: Path
    :return: A mapping of plugins to plugin types
    """
    template = jinja_environment()
    docs_path = Path(path, "docs")
    if docs_path.is_dir():
        logging.info("Purging existing rst files from directory %s", docs_path)
        for entry in docs_path.glob("*.rst"):
            entry.unlink()
    logging.info("Making docs directory %s", docs_path)
    Path(docs_path).mkdir(parents=True, exist_ok=True)

    content = {}

    for subdir in SUBDIRS:  # pylint: disable-msg=too-many-nested-blocks
        if subdir == "modules":
            plugin_type = "module"
        else:
            plugin_type = subdir

        dirpath = Path(path, "plugins", subdir)
        if dirpath.is_dir():
            content[subdir] = {}
            logging.info("Process content in %s", dirpath)
            for filename in os.listdir(dirpath):
                if filename.endswith(".py") and filename not in IGNORE_FILES:
                    fullpath = Path(dirpath, filename)
                    logging.info("Processing %s", fullpath)
                    (
                        doc,
                        examples,
                        return_docs,
                        metadata,
                    ) = plugin_docs.get_docstring(to_text(fullpath), fragment_loader)
                    if doc is None and subdir in ["filter", "test"]:
                        name_only = filename.rsplit(".")[0]
                        combined_ptype = f"{name_only} {subdir}"
                        content[combined_ptype] = handle_simple(collection, fullpath, subdir)
                    else:
                        if doc:
                            doc["plugin_type"] = plugin_type

                            if return_docs:
                                # Seems a recent change in devel makes this
                                # return a dict not a yaml string.
                                if isinstance(return_docs, dict):
                                    doc["return_docs"] = return_docs
                                else:
                                    doc["return_docs"] = yaml.safe_load(return_docs)
                                convert_descriptions(doc["return_docs"])

                            doc["metadata"] = (metadata,)
                            if isinstance(examples, string_types):
                                doc["plain_examples"] = examples.strip()
                            else:
                                doc["examples"] = examples

                            doc["module"] = f"{collection}." "{plugin_name}".format(
                                plugin_name=doc.get(plugin_type, doc.get("name"))
                            )
                            doc["author"] = ensure_list(doc["author"])
                            doc["description"] = ensure_list(doc["description"])
                            try:
                                convert_descriptions(doc["options"])
                            except KeyError:
                                pass  # This module takes no options

                            module_rst_path = Path(
                                path,
                                "docs",
                                doc["module"] + f"_{plugin_type}" + ".rst",
                            )

                            with open(module_rst_path, "w", encoding="utf8") as doc_file:
                                doc_file.write(template.render(doc))
                            content[subdir][doc["module"]] = {
                                "has_rst": True,
                                "comment": doc["short_description"],
                            }
    return content


def load_galaxy(path):
    """Load collection details from the galaxy.yml file in the collection.

    :param path: The path the collection
    :return: The collection name and gh url
    """
    try:
        with open(Path(path, "galaxy.yml"), encoding="utf8") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError:
                logging.error("Unable to parse galaxy.yml in %s", path)
                sys.exit(1)
    except FileNotFoundError:
        logging.error("Unable to find galaxy.yml in %s", path)
        sys.exit(1)


def load_runtime(path):
    """Load runtime details from the runtime.yml file in the collection.

    :param path: The path the collection
    :return: The runtime dict
    """
    try:
        with open(Path(path, "meta/runtime.yml"), encoding="utf8") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError:
                logging.error("Unable to parse runtime.yml in %s", path)
                sys.exit(1)
    except FileNotFoundError:
        logging.error("Unable to find runtime.yml in %s", path)
        sys.exit(1)


def link_collection(path: Path, galaxy: dict, collection_root: Optional[Path] = None):
    """Link the provided collection into the Ansible default collection path.

    :param path: A path
    :type path: Path
    :param galaxy: The galaxy.yml contents
    :type galaxy: dict
    :param collection_root: The root collections path
    """
    if collection_root is None:
        collection_root = Path(Path.home(), ".ansible/collections/ansible_collections")

    namespace_directory = Path(collection_root, galaxy["namespace"])
    collection_directory = Path(namespace_directory, galaxy["name"])

    logging.info("Linking collection to collection path %s", collection_root)
    logging.info("This is required for the Ansible fragment loader to find doc fragments")

    if collection_directory.exists():
        logging.info("Attempting to remove existing %s", collection_directory)

        if collection_directory.is_symlink():
            logging.info("Unlinking: %s", collection_directory)
            collection_directory.unlink()
        else:
            logging.info("Deleting: %s", collection_directory)
            shutil.rmtree(collection_directory)

    logging.info("Creating namespace directory %s", namespace_directory)
    namespace_directory.mkdir(parents=True, exist_ok=True)

    logging.info("Linking collection %s -> %s", path, collection_directory)
    collection_directory.symlink_to(path)


def add_collection(path: Path, galaxy: dict) -> Optional[tempfile.TemporaryDirectory]:
    """Add path to collections dir so we can find local doc_fragments.

    :param path: The collections path
    :param galaxy: The contents of galaxy.yml
    :return: A temporary alternate directory if the collection is not in a valid location
    """
    collections_path = None
    tempdir = None

    try:
        collections_path = path.parents[1]
    except IndexError:
        pass

    # Check that parent dir is named ansible_collections
    if collections_path and collections_path.name != "ansible_collections":
        logging.info("%s doesn't look enough like a collection", collections_path)
        collections_path = None

    if collections_path is None:
        tempdir = tempfile.TemporaryDirectory()  # pylint: disable-msg=consider-using-with
        logging.info("Temporary collection path %s created", tempdir.name)
        collections_path = Path(tempdir.name) / "ansible_collections"
        link_collection(path, galaxy, collection_root=collections_path)

    full_path = collections_path / galaxy["namespace"] / galaxy["name"]
    logging.info("Collection path is %s", full_path)

    # Tell ansible about the path
    _AnsibleCollectionFinder(  # pylint: disable-msg=protected-access
        paths=[collections_path, "~/.ansible/collections"]
    )._install()

    # This object has to outlive this method or it will be cleaned up before
    # we can use it
    return tempdir


def add_ansible_compatibility(runtime, path):
    """Add ansible compatibility information to README.

    :param runtime: runtime.yml contents
    :type runtime: dict
    :param path: A path
    :type path: str
    """
    requires_ansible = runtime.get("requires_ansible")
    if not requires_ansible:
        logging.error("Unable to find requires_ansible in runtime.yml, not added to README")
        return
    readme = os.path.join(path, "README.md")
    try:
        with open(readme, encoding="utf8") as readme_file:
            content = readme_file.read().splitlines()
    except FileNotFoundError:
        logging.error("README.md not found in %s", path)
        logging.error("README.md not updated")
        sys.exit(1)
    try:
        start = content.index("<!--start requires_ansible-->")
        end = content.index("<!--end requires_ansible-->")
    except ValueError:
        logging.error("requires_ansible anchors not found in %s", readme)
        logging.error("README.md not updated with ansible compatibility information")
        sys.exit(1)
    if start and end:
        data = ANSIBLE_COMPAT.format(requires_ansible=requires_ansible).splitlines()
        new = content[0 : start + 1] + data + content[end:]
        with open(readme, "w", encoding="utf8") as readme_file:
            readme_file.write("\n".join(new))
        logging.info("README.md updated with ansible compatibility information")
