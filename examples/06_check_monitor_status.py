#!/usr/bin/env python3
# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
Example 06: Check Specific Monitor Status

Demonstrates how to check the status of a specific monitor by its name or ID.
Supports qualified names in the form '<Monitor name> on <Host name>' to
disambiguate monitors with the same name across different hosts.
Returns the current state (ok, warning, down, unknown) along with
the last polled value and activity status.

For more information: https://ipnetwork-monitor.com/

Usage:
    export MCP_URL="https://your-server:8888/mcp"
    export MCP_TOKEN="your-token"
    python examples/06_check_monitor_status.py <monitor_name_or_id>
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_client import IPNetworkMCPClient, MCPError


def parse_qualified_name(name: str) -> tuple[str, str | None]:
    """Parse a qualified monitor name like 'Ping Check on Test Host' into (monitor, host).

    Returns (monitor_name, host_name) where host_name is None for plain names.
    The split is done on the last occurrence of ' on ' to handle monitor names
    that themselves contain ' on '.
    """
    parts = name.rsplit(" on ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return name, None


async def find_monitor_by_name(client: IPNetworkMCPClient, name: str) -> list[dict]:
    """Search all agents/hosts for monitors matching the given name (case-insensitive).

    Supports qualified names in the form '<Monitor name> on <Host name>'.
    """
    monitor_name, host_name = parse_qualified_name(name)
    matches = []
    agents = await client.list_agents()

    for agent in agents:
        agent_children = await client.list_children("agent", agent["id"], plain=True)
        for hostgroup in agent_children.get("hostGroups", []):
            hg_children = await client.list_children("hostgroup", hostgroup["id"], plain=True)
            for host in hg_children.get("hosts", []):
                if host_name and host["name"].lower() != host_name.lower():
                    continue
                host_children = await client.list_children("host", host["id"], plain=True)
                for monitor in host_children.get("monitors", []):
                    if monitor["name"].lower() == monitor_name.lower():
                        matches.append({
                            "id": monitor["id"],
                            "name": monitor["name"],
                            "host": host["name"],
                            "agent": agent["name"],
                        })

    return matches


async def check_monitor_status(monitor_id_or_name: str) -> int:
    """Check and display the status of a specific monitor. Returns exit code."""
    client = IPNetworkMCPClient.from_env(verify_ssl=False)

    async with client:
        # Determine if argument is an ID or a name
        try:
            monitor_id = int(monitor_id_or_name)
        except ValueError:
            # Search by name
            print(f"Searching for monitor '{monitor_id_or_name}'...")
            matches = await find_monitor_by_name(client, monitor_id_or_name)

            if not matches:
                print(f"Error: No monitor found with name '{monitor_id_or_name}'")
                return 1

            if len(matches) > 1:
                print(f"Multiple monitors found with name '{monitor_id_or_name}':")
                for m in matches:
                    print(f"  ID: {m['id']:5d}  Host: {m['host']}  Agent: {m['agent']}")
                print("\nPlease re-run with a specific monitor ID or qualified name:")
                print('  e.g. "Ping Check on My Host"')
                return 1

            monitor_id = matches[0]["id"]
            print()

        # Get monitor configuration
        try:
            monitor_info = await client.call_tool("get-monitor", {"id": monitor_id})
            name = monitor_info.data.get("name", "Unknown")
            monitor_type = monitor_info.data.get("type", "Unknown")
        except MCPError as e:
            print(f"Error: Could not find monitor with ID {monitor_id}: {e.message}")
            return 1

        # Get current state
        state_data = await client.get_monitor_state(monitor_id)

        state = state_data.get("state", "unknown")
        activity = state_data.get("activity", "unknown")
        last_poll = state_data.get("lastpoll", "N/A")
        current = state_data.get("current", "")
        measure = state_data.get("measure", "")

        # Display results
        print(f"Monitor:    {name} (ID: {monitor_id})")
        print(f"Type:       {monitor_type}")
        print(f"Activity:   {activity}")
        print(f"State:      {state}")
        print(f"Last Poll:  {last_poll}")
        if current:
            print(f"Value:      {current} {measure}".rstrip())

        # Return exit code based on state
        if state.lower() == "down":
            return 2
        elif state.lower() == "warning":
            return 1
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <monitor_name_or_id>")
        print("Examples:")
        print("  python examples/06_check_monitor_status.py 42")
        print('  python examples/06_check_monitor_status.py "HTTP Check"')
        print('  python examples/06_check_monitor_status.py "Ping Check on Test Host"')
        sys.exit(1)

    try:
        exit_code = asyncio.run(check_monitor_status(sys.argv[1]))
        sys.exit(exit_code)
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)
