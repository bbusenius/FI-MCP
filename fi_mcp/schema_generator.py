"""
MCP Schema Generator

Converts FI function signatures to MCP tool schemas automatically.
"""

import logging
import re
from inspect import signature
from typing import Any, Dict, List

from .introspection import (
    convert_type_annotation,
    extract_param_description,
    parse_markdown_docstring,
)

logger = logging.getLogger(__name__)


def generate_mcp_tool_schema(func_name: str, func: callable) -> Dict[str, Any]:
    """
    Convert a FI function to an MCP tool schema.

    Args:
        func_name: Name of the function.
        func: The callable function.

    Returns:
        MCP tool schema dictionary.
    """
    sig = signature(func)
    properties = {}
    required = []

    # Process each parameter
    for param_name, param in sig.parameters.items():
        # Convert type annotation to JSON Schema type
        param_type = convert_type_annotation(param.annotation)

        # Extract parameter description from docstring
        param_description = extract_param_description(func.__doc__, param_name)

        properties[param_name] = {"type": param_type, "description": param_description}

        # Handle special cases for enum/literal types
        annotation_str = str(param.annotation)
        if annotation_str.startswith('typing.Literal'):
            # Extract literal values for enum
            literal_values = _extract_literal_values(annotation_str)
            if literal_values:
                properties[param_name]["enum"] = literal_values

        # Required if no default value
        if param.default == param.empty:
            required.append(param_name)

    # Get function description (first line of docstring)
    description = _get_function_description(func.__doc__)

    return {
        "name": f"fi_{func_name}",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


def _extract_literal_values(type_str: str) -> List[str]:
    """
    Extract literal values from a typing.Literal type string.

    Args:
        type_str: String representation of typing.Literal type.

    Returns:
        List of literal values.
    """
    # Match content inside Literal[...]
    match = re.search(r'Literal\[(.*?)\]', type_str)
    if not match:
        return []

    # Split by comma and clean up quotes
    values = match.group(1).split(',')
    cleaned_values = []

    for value in values:
        value = value.strip().strip('\'"')
        if value:
            cleaned_values.append(value)

    return cleaned_values


def _get_function_description(docstring: str) -> str:
    """
    Extract the main description from a markdown-formatted function docstring.

    Args:
        docstring: Function's docstring.

    Returns:
        Full description paragraph.

    Raises:
        ValueError: If docstring is missing or has no description.
    """
    if not docstring:
        raise ValueError("Function is missing a docstring")

    parsed = parse_markdown_docstring(docstring)
    description = parsed["description"]

    if not description:
        raise ValueError("Docstring has no description section")

    # Normalize whitespace but keep the full description
    return ' '.join(description.split())


def generate_all_tool_schemas(
    fi_functions: Dict[str, callable],
) -> Dict[str, Dict[str, Any]]:
    """
    Generate MCP tool schemas for all FI functions.

    Args:
        fi_functions: Dictionary of function names to callables.

    Returns:
        Dictionary mapping tool names to their schemas.
    """
    schemas = {}

    for func_name, func in fi_functions.items():
        try:
            schema = generate_mcp_tool_schema(func_name, func)
            tool_name = schema["name"]
            schemas[tool_name] = schema
        except Exception as e:
            # Log error but continue with other functions
            logger.error(f"Could not generate schema for {func_name}: {e}")
            continue

    return schemas


def get_tool_schema_summary(schemas: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """
    Get a summary of all tool schemas for debugging/logging.

    Args:
        schemas: Dictionary of tool schemas.

    Returns:
        Dictionary mapping tool names to their descriptions.
    """
    summary = {}

    for tool_name, schema in schemas.items():
        param_count = len(schema.get("parameters", {}).get("properties", {}))
        required_count = len(schema.get("parameters", {}).get("required", []))

        summary[tool_name] = {
            "description": schema.get("description", ""),
            "parameter_count": param_count,
            "required_parameters": required_count,
        }

    return summary
