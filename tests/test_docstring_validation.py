"""
Integration test to validate that all FI functions have proper docstrings.
"""

import pytest

from fi_mcp.introspection import get_fi_functions
from fi_mcp.schema_generator import _get_function_description, generate_mcp_tool_schema


def test_all_fi_functions_have_docstrings():
    """Test that every FI function has a valid docstring with description."""
    fi_functions = get_fi_functions()

    missing_docstrings = []
    invalid_docstrings = []

    for func_name, func in fi_functions.items():
        try:
            description = _get_function_description(func.__doc__)
            # Verify description is not empty after normalization
            assert description, f"{func_name} has empty description"
        except ValueError as e:
            if "missing a docstring" in str(e):
                missing_docstrings.append(func_name)
            elif "no description section" in str(e):
                invalid_docstrings.append(func_name)
            else:
                raise

    # Report any functions with issues
    error_messages = []
    if missing_docstrings:
        error_messages.append(
            f"Functions missing docstrings: {', '.join(missing_docstrings)}"
        )
    if invalid_docstrings:
        error_messages.append(
            f"Functions with invalid docstrings: {', '.join(invalid_docstrings)}"
        )

    if error_messages:
        pytest.fail("\n".join(error_messages))


def test_schema_generation_with_valid_docstring():
    """Test that schema generation works for functions with valid docstrings."""
    fi_functions = get_fi_functions()

    # Test with a known function that should have a good docstring
    func = fi_functions['annual_cost']
    schema = generate_mcp_tool_schema('annual_cost', func)

    assert schema['name'] == 'fi_annual_cost'
    assert 'description' in schema
    assert len(schema['description']) > 0
    assert 'depreciation' in schema['description'].lower()


def test_missing_docstring_raises_error():
    """Test that a function without a docstring raises ValueError."""

    # Create a function without a docstring
    def func_without_docstring(x: int) -> int:
        return x * 2

    with pytest.raises(ValueError, match="missing a docstring"):
        _get_function_description(func_without_docstring.__doc__)


def test_empty_description_raises_error():
    """Test that a docstring with no description section raises ValueError."""
    # Docstring with only Args and Returns, no description
    docstring = """
    ### Args:
    - **x**: some value

    ### Returns:
    The result
    """

    with pytest.raises(ValueError, match="no description section"):
        _get_function_description(docstring)
