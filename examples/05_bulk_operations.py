#!/usr/bin/env python3
# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
Example 05: Bulk Operations

Demonstrates how to perform bulk configuration:
- Create multiple hosts from a list
- Add standard monitors to each host
- Apply consistent settings using inheritance

For more information: https://ipnetwork-monitor.com/

Usage:
    export MCP_URL="https://your-server:8888/mcp"
    export MCP_TOKEN="your-token"
    python examples/05_bulk_operations.py
"""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_client import IPNetworkMCPClient, MCPError


@dataclass
class ServerDefinition:
    """Definition of a server to be monitored."""
    name: str
    ip: str
    icon: str = "Server/Server.png"
    monitors: list[str] | None = None

    def __post_init__(self):
        if self.monitors is None:
            self.monitors = ["ping"]  # Default to ping only


# Configuration - modify this list for your environment
SERVERS_TO_MONITOR = [
    ServerDefinition(
        name="Web Server 1",
        ip="192.168.1.10",
        icon="Server/Web.png",
        monitors=["ping", "http"]
    ),
    ServerDefinition(
        name="Web Server 2",
        ip="192.168.1.11",
        icon="Server/Web.png",
        monitors=["ping", "http"]
    ),
    ServerDefinition(
        name="Database Server",
        ip="192.168.1.20",
        icon="Server/Database.png",
        monitors=["ping", "tcp:3306"]
    ),
    ServerDefinition(
        name="Mail Server",
        ip="192.168.1.30",
        icon="Server/Mail.png",
        monitors=["ping", "tcp:25", "tcp:587"]
    ),
    ServerDefinition(
        name="File Server",
        ip="192.168.1.40",
        icon="Server/File.png",
        monitors=["ping", "tcp:445"]
    ),
]

TARGET_AGENT = "Local Agent"
HOSTGROUP_NAME = "Bulk Import"


async def create_monitor_for_host(
    client: IPNetworkMCPClient,
    host_id: int,
    monitor_spec: str,
    ping_id: int | None = None
) -> tuple[int | None, str]:
    """
    Create a monitor based on specification string.

    Args:
        client: MCP client
        host_id: Parent host ID
        monitor_spec: Monitor specification (e.g., "ping", "http", "tcp:3306")
        ping_id: Optional ping monitor ID for dependency

    Returns:
        Tuple of (monitor_id, monitor_name)
    """
    if monitor_spec == "ping":
        result = await client.create_monitor(
            host_id=host_id,
            name="Ping",
            monitor_type="ping",
            settings={"pollingInterval": "1 min"}
        )
        return result.id, "Ping"

    elif monitor_spec == "http":
        settings = {"pollingInterval": "2 min"}
        if ping_id:
            settings["dependencySettings"] = {
                "mode": "other",
                "monitor": ping_id,
                "state": "down"
            }
        result = await client.create_monitor(
            host_id=host_id,
            name="HTTP Check",
            monitor_type="http",
            config={"URL": "http://$HostIP/"},
            settings=settings
        )
        return result.id, "HTTP Check"

    elif monitor_spec.startswith("tcp:"):
        port = monitor_spec.split(":")[1]
        settings = {"pollingInterval": "2 min"}
        if ping_id:
            settings["dependencySettings"] = {
                "mode": "other",
                "monitor": ping_id,
                "state": "down"
            }
        result = await client.create_monitor(
            host_id=host_id,
            name=f"TCP Port {port}",
            monitor_type="tcp",
            config={"Port": int(port)},
            settings=settings
        )
        return result.id, f"TCP Port {port}"

    else:
        print(f"      Warning: Unknown monitor type '{monitor_spec}'")
        return None, monitor_spec


async def main():
    """Perform bulk host creation."""
    print("=" * 60)
    print("IPNetwork MCP - Bulk Operations Example")
    print("=" * 60)
    print()
    print(f"Servers to create: {len(SERVERS_TO_MONITOR)}")
    for server in SERVERS_TO_MONITOR:
        print(f"  - {server.name} ({server.ip})")
    print()

    client = IPNetworkMCPClient.from_env(verify_ssl=False)

    async with client:
        # Step 1: Find or create host group
        print(f"[Setup] Finding agent '{TARGET_AGENT}'...")
        agent = await client.find_agent(TARGET_AGENT)
        if not agent:
            print(f"        Error: Agent not found")
            sys.exit(1)

        print(f"[Setup] Looking for host group '{HOSTGROUP_NAME}'...")
        hostgroup = await client.find_hostgroup("agent", agent["id"], HOSTGROUP_NAME)

        if hostgroup:
            hostgroup_id = hostgroup["id"]
            print(f"        Found existing host group ID: {hostgroup_id}")
        else:
            print(f"        Creating new host group...")
            try:
                hg_result = await client.call_tool("create-hostgroup", {
                    "parentType": "agent",
                    "parentId": agent["id"],
                    "name": HOSTGROUP_NAME,
                    "config": {
                        "kind": "server",
                        "defaultHostIcon": "Server/Server.png"
                    },
                    "settings": {
                        "pollingInterval": "1 min"
                    }
                })
                hostgroup_id = hg_result.id
                print(f"        Created host group ID: {hostgroup_id}")
            except MCPError as e:
                print(f"        Error: {e.message}")
                sys.exit(1)

        print()
        print("Creating hosts and monitors...")
        print("-" * 50)

        created_hosts = []
        total_monitors = 0

        for i, server in enumerate(SERVERS_TO_MONITOR, 1):
            print(f"[{i}/{len(SERVERS_TO_MONITOR)}] {server.name} ({server.ip})")

            # Create host
            try:
                host_result = await client.create_host(
                    parent_id=hostgroup_id,
                    name=server.name,
                    host_def={"ip": server.ip},
                    icon=server.icon
                )
                host_id = host_result.id
                print(f"      Host created (ID: {host_id})")
                created_hosts.append({
                    "name": server.name,
                    "id": host_id,
                    "monitors": []
                })
            except MCPError as e:
                print(f"      Error creating host: {e.message}")
                continue

            # Create monitors
            ping_id = None
            for monitor_spec in server.monitors:
                try:
                    # Create ping first (if specified) for dependencies
                    if monitor_spec == "ping":
                        monitor_id, monitor_name = await create_monitor_for_host(
                            client, host_id, monitor_spec
                        )
                        ping_id = monitor_id
                    else:
                        monitor_id, monitor_name = await create_monitor_for_host(
                            client, host_id, monitor_spec, ping_id
                        )

                    if monitor_id:
                        print(f"      + {monitor_name} (ID: {monitor_id})")
                        created_hosts[-1]["monitors"].append({
                            "name": monitor_name,
                            "id": monitor_id
                        })
                        total_monitors += 1
                except MCPError as e:
                    print(f"      Error creating {monitor_spec}: {e.message}")

            print()

        # Summary
        print("=" * 60)
        print("Bulk Operation Complete!")
        print("=" * 60)
        print()
        print(f"Host Group: {HOSTGROUP_NAME} (ID: {hostgroup_id})")
        print(f"Hosts Created: {len(created_hosts)}")
        print(f"Monitors Created: {total_monitors}")
        print()

        print("Created Resources:")
        for host in created_hosts:
            print(f"  {host['name']} (ID: {host['id']})")
            for monitor in host["monitors"]:
                print(f"    - {monitor['name']} (ID: {monitor['id']})")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(0)
