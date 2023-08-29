"""A schema validation helper for ansible-creator."""

from __future__ import annotations

from json import JSONDecodeError, loads


try:
    from jsonschema import SchemaError
    from jsonschema.validators import validator_for

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from ansible_creator.exceptions import CreatorError
from ansible_creator.utils import get_file_contents


class SchemaValidator:
    """Class representing a validation engine for ansible-creator content definition files."""

    def __init__(self: SchemaValidator, data: dict, criteria: str) -> None:
        """Initialize the validation engine.

        :param data: Content definition as a dictionary
        :param criteria: Name of the file that contains the JSON schema.
        """
        self.data = data
        self.criteria = criteria

    def validate(self: SchemaValidator) -> list:
        """Validate data against loaded schema.

        :returns: A list of schema validation errors (if any).
        :raises CreatorError: if sanity check for schema fails.
        """
        errors = []
        schema = self.load_schema()
        validator = validator_for(schema)

        try:
            validator.check_schema(schema)
        except SchemaError as schema_err:
            msg = "Sanity check failed for in-built schema. This is likely a bug.\n"
            raise CreatorError(
                msg,
            ) from schema_err

        validation_errors = sorted(
            validator(schema).iter_errors(self.data),
            key=lambda e: e.path,
        )

        for err in validation_errors:
            err_msg = "* " + str(err.message) + " at " + str(err.instance) + "\n"
            errors.append(err_msg)

        return errors

    def load_schema(self: SchemaValidator) -> dict:
        """Attempt to load the schema from schemas directory.

        :returns: A schema loaded as json.
        :raises CreatorError: if the JSON schema cannot be loaded.
        """
        try:
            schema: dict = loads(get_file_contents("schemas", self.criteria))
        except (
            FileNotFoundError,
            TypeError,
            JSONDecodeError,
            ModuleNotFoundError,
        ) as err:
            msg = "Unable to load jsonschema for validation with error(s):\n"
            raise CreatorError(
                msg,
            ) from err

        return schema
