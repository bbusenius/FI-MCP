"""
FI-MCP Server

Main MCP server implementation that auto-generates tools from FI functions.
"""

import asyncio
import logging
from inspect import cleandoc, signature
from typing import Any, Dict

from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, ServerCapabilities, TextContent, Tool

from .introspection import get_fi_functions, get_mcp_func_args, validate_mcp_arguments
from .schema_generator import generate_all_tool_schemas, get_tool_schema_summary

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NO_DOCUMENTATION_AVAILABLE = "No documentation available."

# Create MCP server instance
app = Server("fi-mcp")

# Module-level storage for FI functions and their schemas.
# Note: Use of mutable global state is generally discouraged in Python, but it's
# acceptable here because:
# 1. Server initialization happens once at startup
# 2. These act as read-only caches after initialization
# 3. MCP handlers need fast, direct access without re-discovering functions
# 4. The server runs as a single-process daemon with no concurrent modifications
fi_functions: Dict[str, callable] = {}
tool_schemas: Dict[str, Dict[str, Any]] = {}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List all available FI tools.

    Returns:
        List of Tool objects for all FI functions.
    """
    tools = []

    for tool_name, schema in tool_schemas.items():
        tool = Tool(
            name=schema["name"],
            description=schema["description"],
            inputSchema=schema["parameters"],
        )
        tools.append(tool)

    logger.info(f"Listed {len(tools)} FI tools")
    return tools


def _format_function_name(func_name: str) -> str:
    """
    Convert function_name to Function Name (Title Case).

    Special handling for abbreviations:
    - FI (Financial Independence) is always uppercase
    - POT (Pay-Over-Tuition) is always uppercase

    Args:
        func_name: Function name with underscores.

    Returns:
        Formatted name with spaces and title case.
    """
    formatted = func_name.replace('_', ' ').title()
    # Handle special abbreviations
    formatted = formatted.replace('Fi', 'FI')
    formatted = formatted.replace('Pot', 'POT')
    return formatted


def _get_function_docstring(func: callable) -> str:
    """
    Get cleaned docstring from a function.

    Args:
        func: Function to extract docstring from.

    Returns:
        Cleaned docstring or fallback message.
    """
    return cleandoc(func.__doc__) if func.__doc__ else NO_DOCUMENTATION_AVAILABLE


def _format_function_help(
    func_name: str, func: callable, heading_level: int = 1
) -> str:
    """
    Format a single function's help documentation.

    Args:
        func_name: Name of the function.
        func: The function object.
        heading_level: Markdown heading level (1 for #, 2 for ##, etc).

    Returns:
        Formatted markdown help text.
    """
    docstring = _get_function_docstring(func)
    display_name = _format_function_name(func_name)
    heading = "#" * heading_level
    return f"{heading} {display_name}\n\n{docstring}"


def _create_resource_contents(content: str) -> list[ReadResourceContents]:
    """
    Create ReadResourceContents with markdown mime type.

    Args:
        content: Markdown content.

    Returns:
        List containing single ReadResourceContents object.
    """
    return [ReadResourceContents(content=content, mime_type="text/markdown")]


@app.list_resources()
async def list_resources() -> list[Resource]:
    """
    List all available help resources.

    Returns:
        List of Resource objects for FI function documentation.
    """
    resources = []

    # Add individual function help resources
    for func_name in fi_functions.keys():
        resource = Resource(
            uri=f"fi://help/{func_name}",
            name=f"Help: {func_name}",
            description=f"Documentation for the {func_name} function",
            mimeType="text/markdown",
        )
        resources.append(resource)

    # Add a resource for all help
    resources.append(
        Resource(
            uri="fi://help/all",
            name="Help: All Functions",
            description="Documentation for all FI functions",
            mimeType="text/markdown",
        )
    )

    logger.info(f"Listed {len(resources)} help resources")
    return resources


@app.read_resource()
async def read_resource(uri: str) -> list[ReadResourceContents]:
    """
    Read a help resource.

    Args:
        uri: URI of the resource to read.

    Returns:
        List of resource contents with markdown.
    """
    # Convert AnyUrl to string if needed
    uri_str = str(uri)
    logger.info(f"Reading resource: {uri_str}")

    if not uri_str.startswith("fi://help/"):
        raise ValueError(f"Unknown resource URI: {uri_str}")

    # Extract function name from URI
    func_name = uri_str.replace("fi://help/", "")

    if func_name == "all":
        all_help = [
            _format_function_help(name, func, heading_level=2)
            for name, func in sorted(fi_functions.items())
        ]
        content = "\n\n---\n\n".join(all_help)
        return _create_resource_contents(content)

    elif func_name in fi_functions:
        func = fi_functions[func_name]
        content = _format_function_help(func_name, func, heading_level=1)
        return _create_resource_contents(content)

    else:
        raise ValueError(f"Unknown function: {func_name}")


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Execute a FI function tool.

    Args:
        name: Name of the tool to call.
        arguments: Arguments passed to the tool.

    Returns:
        Tool execution result.
    """
    logger.info(f"Calling tool: {name} with arguments: {arguments}")

    # Remove 'fi_' prefix to get function name
    if not name.startswith('fi_'):
        raise ValueError(f"Invalid tool name: {name}")

    func_name = name[3:]  # Remove 'fi_' prefix

    if func_name not in fi_functions:
        raise ValueError(f"Unknown function: {func_name}")

    function_to_call = fi_functions[func_name]

    try:
        # Get function signature
        sig = signature(function_to_call)
        fun_params = sig.parameters

        # Validate required arguments
        missing_args = validate_mcp_arguments(fun_params, arguments)
        if missing_args:
            error_msg = f"Missing required arguments: {', '.join(missing_args)}"
            return [TextContent(type="text", text=f"Error: {error_msg}")]

        # Convert arguments to proper types
        fail, fun_args = get_mcp_func_args(fun_params, arguments)
        if fail:
            return [TextContent(type="text", text="Error: Failed to convert arguments")]

        # Call the FI function
        result = function_to_call(*fun_args)

        # Format result as string
        result_text = str(result)

        logger.info(f"Tool {name} executed successfully: {result_text}")
        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


def initialize_server():
    """
    Initialize the server by discovering FI functions and generating schemas.
    """
    global fi_functions, tool_schemas

    logger.info("Initializing FI-MCP server...")

    # Discover all FI functions
    fi_functions = get_fi_functions()
    logger.info(f"Discovered {len(fi_functions)} FI functions")

    # Generate MCP tool schemas
    tool_schemas = generate_all_tool_schemas(fi_functions)
    logger.info(f"Generated {len(tool_schemas)} tool schemas")

    # Log summary
    summary = get_tool_schema_summary(tool_schemas)
    for tool_name, info in summary.items():
        logger.debug(
            f"Tool: {tool_name} - {info['parameter_count']} params "
            f"({info['required_parameters']} required)"
        )

    logger.info("FI-MCP server initialization complete")


async def main():
    """
    Main entry point for the MCP server.
    """
    # Initialize the server
    initialize_server()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fi-mcp",
                server_version="0.1.0",
                capabilities=ServerCapabilities(tools={}, resources={}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
