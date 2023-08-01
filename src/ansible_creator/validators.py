"""A schema validation helper for ansible-creator."""

from json import JSONDecodeError, loads


try:
    from jsonschema import SchemaError
    from jsonschema.validators import validator_for

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
from .utils import get_file_contents


class JSONSchemaValidator:
    """Class representing a validation engine for ansible-creator content definition files."""

    def __init__(self, data, criteria):
        """Initialize the validation engine.

        :param data: Content definition as a dictionary
        :param criteria: Name of the file that contains the JSON schema.
        """
        self.data = data
        try:
            self.schema = loads(get_file_contents("schemas", criteria))
        except (FileNotFoundError, TypeError, JSONDecodeError) as err:
            raise Exception(
                f"unable to load schema for validation with error:\n{str(err)}"
            )

    def validate(self):
        """Validate data against loaded schema.

        :returns: A list of schema validation errors (if any)
        """
        errors = []
        validator = validator_for(self.schema)
        try:
            validator.check_schema(self.schema)
        except SchemaError as schema_err:
            raise Exception(
                "Sanity check failed for in-built schema. This is likely a bug."
                f"\n\n{str(schema_err)}"
            )

        validation_errors = sorted(
            validator(self.schema).iter_errors(self.data), key=lambda e: e.path
        )

        for err in validation_errors:
            err_msg = str(err.message) + " at " + str(err.instance) + "\n"
            errors.append(err_msg)

        return errors
