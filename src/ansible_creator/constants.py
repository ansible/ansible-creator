"""Definition of constants for this package."""

OPTION_CONDITIONALS = (
    "mutually_exclusive",
    "required_one_of",
    "required_together",
    "required_by",
    "required_if",
)

OPTION_METADATA = (
    "type",
    "choices",
    "default",
    "required",
    "aliases",
    "elements",
    "fallback",
    "no_log",
    "apply_defaults",
    "deprecated_aliases",
    "removed_in_version",
)

VALID_ANSIBLEMODULE_ARGS = (
    "bypass_checks",
    "no_log",
    "add_file_common_args",
    "supports_check_mode",
    *OPTION_CONDITIONALS,
)
