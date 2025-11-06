# FI-MCP

Model Context Protocol (MCP) server for the Financial Independence community.

## Overview

FI-MCP automatically generates MCP tools from the FI function library using introspection.
This allows AI assistants to access the financial independence calculation functions we
use as native tools. This gets rid of hallucinations by ensuring that the AI uses the
right calculations for the job, rather than guessing or taking a random calculation from
the web. It also boosts confidence for the user because it allows us to know where the
calculation is coming from. Math can be checked in the [FI library](https://github.com/bbusenius/FI)
and the associated blog article or forum link (where applicable).

<img width="962" height="1357" alt="image" src="https://github.com/user-attachments/assets/7f52eda5-5397-4d0c-bc27-7a43b4862560" />

## Features

- **Auto-discovery**: Automatically finds all functions in the FI library
- **Type-safe**: Converts Python type annotations to MCP tool schemas
- **Parameter validation**: Validates and converts arguments before function calls
- **Comprehensive coverage**: All 30+ FI functions available as MCP tools

## Installation

For development:

```bash
# Clone the repository
cd /path/to/FI-MCP

# Install package with dev dependencies in editable mode
pip install -e .[dev]
```

For production use:

```bash
pip install .
```

## Configuration for AI Editors

Add these setttings to your Windsurf MCP config file, Claude `~/.claude/config.json`,
or other analogous file:

```json
{
  "mcpServers": {
    "fi-mcp": {
      "command": "python",
      "args": ["-m", "fi_mcp.server"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

After adding the configuration, restart your editor. The AI assistant will now have
access to all FI calculation tools.

## Usage

Once configured, you can ask your AI assistant questions like:

- "Calculate my CoastFI number with $50k invested, 4% return, retiring at 65, currently 30"
- "How much does it cost to buy a day of freedom with $40k annual spending?"
- "How do I calculate cap rate?" - Get full documentation including what it calculates, parameters, and credits
- "I don't remember how to calculate turnover costs" - Get full documentation including what it calculates, parameters, and credits
- "What inputs does future_value take?" - See all parameters with descriptions
- "Show me all available FI calculations" - Browse all available functions

The AI will automatically use the appropriate FI tool to perform a FI related calculation.
It can access complete markdown-formatted docstrings for any function, including detailed
explanations, parameter descriptions, return values, and attribution credits.

## Available Tools

See the [FI library](https://github.com/bbusenius/FI) for the full list of available tools. 

## Architecture

FI-MCP uses introspection patterns to:

1. Discover all functions in the FI module
2. Extract parameter types and descriptions from function signatures and markdown docstrings
3. Generate MCP tool schemas automatically
4. Expose function documentation via MCP Resources
5. Handle type conversion and validation
6. Execute functions with converted arguments

### MCP Features

- **Tools**: Each FI function is exposed as an MCP tool with full type information and parameter descriptions
- **Resources**: Function documentation is available via `fi://help/{function_name}` URIs, returning markdown-formatted docstrings

## Development

### Setup

Install the package in editable mode with development dependencies:

```bash
pip install -e .[dev]
```

### Running Tests

Run all tests:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_docstring_validation.py -v
pytest tests/test_basic.py -v
```

### Test Coverage

- `tests/test_docstring_validation.py` - Validates that all FI functions have proper markdown docstrings
- `tests/test_basic.py` - Integration tests for function discovery, schema generation, and execution

## License

MIT License - Same as FI library
