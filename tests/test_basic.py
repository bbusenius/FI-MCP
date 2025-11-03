#!/usr/bin/env python3
"""
Basic integration tests for FI-MCP functionality
"""

from decimal import Decimal
from inspect import signature

import fi
import pytest

from fi_mcp.introspection import get_fi_functions, get_mcp_func_args
from fi_mcp.schema_generator import generate_all_tool_schemas


@pytest.fixture(scope="module")
def fi_functions():
    """Fixture that discovers all FI functions once per module"""
    return get_fi_functions()


def test_function_discovery(fi_functions):
    """Test that we can discover FI functions"""
    assert len(fi_functions) > 0, "Should discover at least one function"
    assert all(
        callable(func) for func in fi_functions.values()
    ), "All discovered items should be callable"

    # Verify we have some expected functions
    assert 'future_value' in fi_functions, "Should discover future_value function"


def test_schema_generation(fi_functions):
    """Test MCP schema generation"""
    schemas = generate_all_tool_schemas(fi_functions)

    assert len(schemas) > 0, "Should generate at least one schema"
    assert len(schemas) == len(fi_functions), "Should generate schema for each function"

    # Test a specific function schema
    assert 'fi_future_value' in schemas, "Should have schema for future_value"

    schema = schemas['fi_future_value']
    assert schema['name'] == 'fi_future_value', "Schema should have correct name"
    assert 'description' in schema, "Schema should have description"
    assert 'parameters' in schema, "Schema should have parameters"
    assert 'properties' in schema['parameters'], "Parameters should have properties"
    assert 'required' in schema['parameters'], "Parameters should have required list"

    # Verify required parameters
    required_params = schema['parameters']['required']
    assert 'present_value' in required_params, "present_value should be required"
    assert 'annual_rate' in required_params, "annual_rate should be required"


def test_specific_function():
    """Test calling a specific FI function with argument conversion"""
    # Test future_value function
    func = fi.future_value
    sig = signature(func)

    # Mock MCP arguments
    mcp_args = {
        'present_value': 1000,
        'annual_rate': 7,
        'periods_per_year': 1,
        'years': 10,
    }

    fail, converted_args = get_mcp_func_args(sig.parameters, mcp_args)

    assert not fail, "Argument conversion should succeed"
    assert len(converted_args) > 0, "Should have converted arguments"
    assert len(converted_args) >= len(
        mcp_args
    ), "Should have at least as many args as provided (includes defaults)"

    # Call the function
    result = func(*converted_args)
    assert result > 1000, "Future value should be greater than present value"
    assert isinstance(result, (int, float, Decimal)), "Result should be numeric"
