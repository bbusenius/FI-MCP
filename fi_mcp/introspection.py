"""
Introspection utilities for FI-MCP

Adapted from FI-API introspection patterns to work with MCP instead of Flask.
Handles function discovery, parameter extraction, type conversion, and validation.
"""

import re
from inspect import cleandoc
from typing import Any, Dict, List, Tuple

import fi
from diablo_utils import functs_from_mod


def get_fi_functions() -> Dict[str, callable]:
    """
    Discover all functions from the FI module.

    Returns:
        Dictionary mapping function names to callable functions.
    """
    return functs_from_mod(fi)


def get_mcp_func_args(
    fun_params: Dict, mcp_arguments: Dict[str, Any]
) -> Tuple[bool, List[Any]]:
    """
    Retrieves function arguments from MCP tool arguments.

    Unlike FI-API which receives all arguments as strings from URL parameters,
    MCP provides pre-typed arguments via JSON schema validation. We can use
    these directly without type casting.

    Args:
        fun_params: parameters from an inspect.signature.
        mcp_arguments: arguments passed to the MCP tool (already typed).

    Returns:
        A tuple where the first item is a boolean and the second item is a
        list of arguments to pass to a function. The boolean will be
        set to True if an expected argument is missing.
    """
    fun_args = []
    fail = False

    for key in fun_params.keys():
        arg_name = fun_params[key].name
        arg_passed = mcp_arguments.get(arg_name)

        # If argument not provided, check if it has a default
        if arg_passed is None:
            if fun_params[key].default == fun_params[key].empty:
                # Required parameter is missing
                fail = True
                break
            else:
                # Optional parameter - use default
                fun_args.append(fun_params[key].default)
                continue

        # MCP arguments are already properly typed from JSON schema
        # Just use them directly
        fun_args.append(arg_passed)

    return (fail, fun_args)


def parse_markdown_docstring(docstring: str) -> Dict[str, Any]:
    """
    Parse markdown-formatted docstring into structured sections.

    Args:
        docstring: Markdown-formatted function docstring.

    Returns:
        Dictionary with 'description', 'args', and 'returns' sections.
    """
    if not docstring:
        return {"description": "", "args": {}, "returns": ""}

    cleaned = cleandoc(docstring)

    # Extract description (everything before ### Args:)
    desc_match = re.match(r'(.*?)(?=###|$)', cleaned, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    # Extract Args section
    args_dict = {}
    args_match = re.search(r'### Args:\s*\n(.*?)(?=\n###|\Z)', cleaned, re.DOTALL)
    if args_match:
        args_text = args_match.group(1)
        # Find all parameter entries: - **param_name**: description
        param_pattern = r'-\s*\*\*(\w+)\*\*:\s*([^\n]+(?:\n(?!\s*-)[^\n]+)*)'
        for match in re.finditer(param_pattern, args_text):
            param_name = match.group(1)
            param_desc = re.sub(r'\s+', ' ', match.group(2)).strip()
            args_dict[param_name] = param_desc

    # Extract Returns section
    returns = ""
    returns_match = re.search(r'### Returns:\s*\n(.*?)(?=\n###|\Z)', cleaned, re.DOTALL)
    if returns_match:
        returns = re.sub(r'\s+', ' ', returns_match.group(1)).strip()

    return {"description": description, "args": args_dict, "returns": returns}


def extract_param_description(docstring: str, param_name: str) -> str:
    """
    Extract parameter description from markdown-formatted function docstring.

    Args:
        docstring: Function's docstring.
        param_name: Name of the parameter to extract description for.

    Returns:
        Description of the parameter, or generic description if not found.
    """
    parsed = parse_markdown_docstring(docstring)
    return parsed["args"].get(param_name, f"Parameter: {param_name}")


def convert_type_annotation(type_annotation: type) -> str:
    """
    Convert Python type annotation to JSON Schema type.

    Args:
        type_annotation: Python type annotation.

    Returns:
        JSON Schema type string.
    """
    type_str = str(type_annotation)

    # Check for container types first (before basic types)
    # Otherwise List[float] would match 'float' before 'List'
    #
    # Dual checks (type_annotation == float or 'float' in type_str):
    # - Direct type comparison for standard annotations
    # - String-based check for string annotations, forward references,
    #   and code that explicitly uses `from __future__ import annotations`
    #   (PEP 563 opt-in behavior that makes all annotations strings)
    # - This is just defensive programming
    if 'List' in type_str or 'list' in type_str:
        return "array"
    elif 'Dict' in type_str or 'dict' in type_str:
        return "object"
    # Handle basic types
    elif type_annotation == float or 'float' in type_str:
        return "number"
    elif type_annotation == int or 'int' in type_str:
        return "integer"
    elif type_annotation == str or 'str' in type_str:
        return "string"
    elif type_annotation == bool or 'bool' in type_str:
        return "boolean"
    else:
        # Default to string for custom types like Money, Percent, etc.
        return "string"


def validate_mcp_arguments(
    fun_params: Dict, mcp_arguments: Dict[str, Any]
) -> List[str]:
    """
    Validate that all required MCP arguments are provided.

    Args:
        fun_params: Function parameters from inspect.signature.
        mcp_arguments: Arguments passed to MCP tool.

    Returns:
        List of missing required parameter names (empty if all provided).
    """
    missing = []

    for param_name, param in fun_params.items():
        if param.default == param.empty and param_name not in mcp_arguments:
            missing.append(param_name)

    return missing
