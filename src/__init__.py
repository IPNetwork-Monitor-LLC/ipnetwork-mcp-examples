# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# IPNetwork MCP Client Library
"""
IPNetwork MCP Client - A Python wrapper for the IPNetwork Monitor MCP API.

For more information about IPNetwork Monitor, visit:
https://ipnetwork-monitor.com/
"""

from .mcp_client import IPNetworkMCPClient, MCPError

__version__ = "1.0.0"
__all__ = ["IPNetworkMCPClient", "MCPError"]
