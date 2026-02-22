#!/usr/bin/env python3
# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
Example 01: Basic Connection

Demonstrates how to connect to the IPNetwork MCP server and list available agents.
For more information: https://ipnetwork-monitor.com/

Usage:
    export MCP_URL="https://your-server:8888/mcp"
    export MCP_TOKEN="your-token"
    python examples/01_basic_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_client import IPNetworkMCPClient, MCPError


async def main():
    """Connect to MCP server and list agents."""
    print("=" * 60)
    print("IPNetwork MCP - Basic Connection Example")
    print("=" * 60)
    print()

    try:
        # Create client from environment variables
        # Set verify_ssl=False for self-signed certificates
        client = IPNetworkMCPClient.from_env(verify_ssl=False)

        async with client:
            print("Connected to MCP server successfully!")
            print()

            # List all agents
            print("Available Agents:")
            print("-" * 40)
            agents = await client.list_agents()

            for agent in agents:
                print(f"  ID: {agent['id']:3d} | Name: {agent['name']}")

            print()
            print(f"Total agents: {len(agents)}")

            # Show children of the first agent
            if agents:
                print()
                print(f"Children of '{agents[0]['name']}':")
                print("-" * 40)

                children = await client.list_children("agent", agents[0]["id"], plain=True)

                hostgroups = children.get("hostGroups", [])
                for hg in hostgroups:
                    print(f"  [Group] {hg['name']} (ID: {hg['id']})")

    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except MCPError as e:
        print(f"MCP Error: {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"Connection Error: {e}")
        print()
        print("Make sure:")
        print("  1. IPNetwork Monitor is running with MCP enabled")
        print("  2. MCP_URL points to the correct server and port")
        print("  3. MCP_TOKEN is valid")
        sys.exit(1)

    print()
    print("Connection test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
