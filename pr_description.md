## Overview

This PR fixes all DOC502 pydoclint errors by removing inappropriate 'Raises'
sections from test function docstrings that only use assert statements.

## Problem

The pydoclint baseline file contained 55 DOC502 errors across 11 test files.
These errors occurred because test functions had 'Raises: AssertionError: If the
assertion fails.' sections in their docstrings, but the functions only used
pytest's assert mechanism rather than explicit raise statements.

According to pydoclint DOC502 rules, functions should only document exceptions
in their 'Raises' sections if they explicitly raise those exceptions using raise
statements.

## Solution

- Removed inappropriate 'Raises: AssertionError' sections from 55 test functions
- Preserved all other docstring content (descriptions, Args sections, etc.)
- Maintained proper docstring formatting
- Cleared .config/pydoclint-baseline.txt as all errors are now resolved

## Files Changed

### Test Files Fixed (55 functions total):

- tests/fixtures/collection/testorg/testcol/tests/integration/test_integration.py
  (1 function)
- tests/fixtures/collection/testorg/testcol/tests/unit/test_basic.py (1
  function)
- tests/integration/test_init.py (7 functions)
- tests/integration/test_lint.py (2 functions)
- tests/units/test_add.py (10 functions)
- tests/units/test_argparse_help.py (2 functions)
- tests/units/test_basic.py (12 functions)
- tests/units/test_compat.py (1 function)
- tests/units/test_init.py (8 functions)
- tests/units/test_templar.py (3 functions)
- tests/units/test_utils.py (8 functions)

### Configuration:

- .config/pydoclint-baseline.txt (cleared - all errors resolved)

## Impact

- ✅ All DOC502 pydoclint errors resolved
- ✅ Improved docstring accuracy and consistency
- ✅ No functional changes to test behavior
- ✅ Maintains all existing test documentation

## Testing

All existing tests continue to pass as this change only affects docstring
documentation, not test functionality.

## Example of Changes Made

**Before:**

```python
def test_example() -> None:
    """Test example function.

    Raises:
        AssertionError: If the assertion fails.
    """
    assert True
```

**After:**

```python
def test_example() -> None:
    """Test example function."""
    assert True
```

The 'Raises' section was removed because the function uses pytest's assert
mechanism, not explicit raise statements.
