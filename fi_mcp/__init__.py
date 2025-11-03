"""
FI-MCP: Model Context Protocol server for Financial Independence calculations

Auto-generates MCP tools from the FI function library using introspection.
"""

__version__ = "0.1.0"
__author__ = "Brad Busenius"

from .server import app, main

__all__ = ["app", "main"]
