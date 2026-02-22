#!/usr/bin/env python3
# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
Example 02: Create Host with Monitors

Demonstrates how to:
- Find an existing host group
- Create a new host
- Add Ping and HTTP monitors with dependencies
- Query monitor state

For more information: https://ipnetwork-monitor.com/

Usage:
    export MCP_URL="https://your-server:8888/mcp"
    export MCP_TOKEN="your-token"
    python examples/02_create_host.py
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_client import IPNetworkMCPClient, MCPError


# Configuration - modify these values as needed
TARGET_AGENT = "Local Agent"
TARGET_HOSTGROUP = "Desktops and Notebooks"
HOST_NAME = "Example Host"
HOST_DOMAIN = "example.com"


async def main():
    """Create a host with monitors."""
    print("=" * 60)
    print("IPNetwork MCP - Create Host Example")
    print("=" * 60)
    print()

    client = IPNetworkMCPClient.from_env(verify_ssl=False)

    async with client:
        # Step 1: Find the target agent
        print(f"[1/5] Finding agent '{TARGET_AGENT}'...")
        agent = await client.find_agent(TARGET_AGENT)
        if not agent:
            print(f"      Error: Agent '{TARGET_AGENT}' not found")
            sys.exit(1)
        print(f"      Found agent ID: {agent['id']}")

        # Step 2: Find the target host group
        print(f"[2/5] Finding host group '{TARGET_HOSTGROUP}'...")
        hostgroup = await client.find_hostgroup("agent", agent["id"], TARGET_HOSTGROUP)
        if not hostgroup:
            print(f"      Error: Host group '{TARGET_HOSTGROUP}' not found")
            print("      Available host groups:")
            children = await client.list_children("agent", agent["id"], plain=True)
            for hg in children.get("hostGroups", []):
                print(f"        - {hg['name']}")
            sys.exit(1)
        print(f"      Found host group ID: {hostgroup['id']}")

        # Step 3: Create the host
        print(f"[3/5] Creating host '{HOST_NAME}'...")
        try:
            host_result = await client.create_host(
                parent_id=hostgroup["id"],
                name=HOST_NAME,
                host_def={"name": HOST_DOMAIN},
                icon="Server/Web.png"
            )
            host_id = host_result.id
            print(f"      Created host ID: {host_id}")
            if host_result.warnings:
                print(f"      Warnings: {', '.join(host_result.warnings)}")
        except MCPError as e:
            print(f"      Error creating host: {e.message}")
            sys.exit(1)

        # Step 4: Create a Ping monitor
        print("[4/5] Creating Ping monitor...")
        try:
            ping_result = await client.create_monitor(
                host_id=host_id,
                name="Ping Check",
                monitor_type="ping",
                config={
                    "Packet size": 1024
                },
                settings={
                    "pollingInterval": "1 min"
                }
            )
            ping_id = ping_result.id
            print(f"      Created Ping monitor ID: {ping_id}")
        except MCPError as e:
            print(f"      Error creating Ping monitor: {e.message}")
            sys.exit(1)

        # Step 5: Create an HTTP monitor with dependency on Ping
        print("[5/5] Creating HTTP monitor (depends on Ping)...")
        try:
            http_result = await client.create_monitor(
                host_id=host_id,
                name="HTTPS Check",
                monitor_type="http",
                config={
                    "URL": f"https://{HOST_DOMAIN}",
                    "Method": "GET"
                },
                settings={
                    "pollingInterval": "2 min",
                    "dependencySettings": {
                        "mode": "other",
                        "monitor": ping_id,
                        "state": "down"
                    }
                }
            )
            http_id = http_result.id
            print(f"      Created HTTP monitor ID: {http_id}")
        except MCPError as e:
            print(f"      Error creating HTTP monitor: {e.message}")
            sys.exit(1)

        print()
        print("Host and monitors created successfully!")
        print()

        # Wait for first poll and show status
        print("Waiting for first poll (10 seconds)...")
        time.sleep(10)

        print()
        print("Monitor States:")
        print("-" * 40)

        for monitor_name, monitor_id in [("Ping", ping_id), ("HTTP", http_id)]:
            try:
                state = await client.get_monitor_state(monitor_id)
                status = state.get("state", "unknown")
                activity = state.get("activity", "unknown")
                current = state.get("current", "N/A")
                measure = state.get("measure", "")
                print(f"  {monitor_name}: {status} ({activity}) - {current} {measure}")
            except MCPError as e:
                print(f"  {monitor_name}: Error - {e.message}")

        print()
        print("Summary:")
        print(f"  Host ID: {host_id}")
        print(f"  Ping Monitor ID: {ping_id}")
        print(f"  HTTP Monitor ID: {http_id}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(0)
