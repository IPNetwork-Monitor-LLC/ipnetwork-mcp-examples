#!/usr/bin/env python3
# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
Example 04: Monitor State Queries

Demonstrates how to query monitor states and statistics:
- Get current state of all monitors
- Get state change history
- Get graph data for charting
- Get statistical summaries

For more information: https://ipnetwork-monitor.com/

Usage:
    export MCP_URL="https://your-server:8888/mcp"
    export MCP_TOKEN="your-token"
    python examples/04_monitor_state.py [monitor_id]
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_client import IPNetworkMCPClient, MCPError


def format_state(state: str) -> str:
    """Format state with visual indicator."""
    indicators = {
        "ok": "[OK]",
        "warning": "[WARN]",
        "down": "[DOWN]",
        "unknown": "[?]"
    }
    return indicators.get(state.lower(), f"[{state}]")


async def show_all_monitors(client: IPNetworkMCPClient):
    """Show current state of all monitors."""
    print("Scanning all monitors...")
    print()

    agents = await client.list_agents()

    total_monitors = 0
    state_counts = {"ok": 0, "warning": 0, "down": 0, "unknown": 0}

    for agent in agents:
        children = await client.list_children("agent", agent["id"], plain=True)
        hosts = children.get("hosts", [])

        if not hosts:
            continue

        print(f"Agent: {agent['name']}")
        print("-" * 50)

        for host in hosts:
            host_children = await client.list_children("host", host["id"], plain=True)
            monitors = host_children.get("monitors", [])

            if monitors:
                print(f"  Host: {host['name']}")

            for monitor in monitors:
                try:
                    state_data = await client.get_monitor_state(monitor["id"])
                    state = state_data.get("state", "unknown")
                    activity = state_data.get("activity", "unknown")
                    current = state_data.get("current", "")
                    measure = state_data.get("measure", "")

                    state_counts[state.lower()] = state_counts.get(state.lower(), 0) + 1
                    total_monitors += 1

                    value_str = f"{current} {measure}".strip() if current else ""
                    print(f"    {format_state(state):8} {monitor['name'][:30]:30} {value_str}")
                except MCPError:
                    print(f"    [ERR]    {monitor['name'][:30]:30} (error reading state)")

        print()

    print("=" * 50)
    print(f"Summary: {total_monitors} monitors")
    print(f"  OK: {state_counts.get('ok', 0)}")
    print(f"  Warning: {state_counts.get('warning', 0)}")
    print(f"  Down: {state_counts.get('down', 0)}")
    print(f"  Unknown: {state_counts.get('unknown', 0)}")


async def show_monitor_details(client: IPNetworkMCPClient, monitor_id: int):
    """Show detailed information for a specific monitor."""
    print(f"Monitor Details (ID: {monitor_id})")
    print("=" * 50)
    print()

    # Get monitor configuration
    try:
        monitor_config = await client.call_tool("get-monitor", {"id": monitor_id})
        print(f"Name: {monitor_config.data.get('name', 'Unknown')}")
        print(f"Type: {monitor_config.data.get('type', 'Unknown')}")
        print()
    except MCPError as e:
        print(f"Error getting monitor config: {e.message}")
        return

    # Current state
    print("Current State:")
    print("-" * 30)
    try:
        state = await client.get_monitor_state(monitor_id)
        print(f"  Activity: {state.get('activity', 'N/A')}")
        print(f"  State: {state.get('state', 'N/A')}")
        print(f"  Last Poll: {state.get('lastpoll', 'N/A')}")
        print(f"  Current Value: {state.get('current', 'N/A')} {state.get('measure', '')}")
    except MCPError as e:
        print(f"  Error: {e.message}")
    print()

    # State history (last 24 hours)
    print("State History (last 24 hours):")
    print("-" * 30)
    try:
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        history = await client.get_monitor_history(
            monitor_id,
            start=yesterday.isoformat(),
            finish=now.isoformat()
        )

        if history:
            for event in history[-10:]:  # Show last 10 events
                start_str = event.get("start", "")[:19]  # Trim to seconds
                stop_str = event.get("stop", "")[:19]
                state = event.get("state", "?")
                activity = event.get("activity", "?")
                print(f"  {start_str} - {stop_str}: {state} ({activity})")
            if len(history) > 10:
                print(f"  ... and {len(history) - 10} more events")
        else:
            print("  No state changes in the last 24 hours")
    except MCPError as e:
        print(f"  Error: {e.message}")
    print()

    # Graph data sample
    print("Graph Data Sample (last hour):")
    print("-" * 30)
    try:
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        graph_result = await client.call_tool("monitor-state", {
            "type": "graph",
            "id": monitor_id,
            "start": hour_ago.isoformat(),
            "finish": now.isoformat()
        })

        graph_data = graph_result.data.get("graph", [])
        if graph_data:
            # Show first and last few data points
            print(f"  {len(graph_data)} data points")
            for point in graph_data[:3]:
                time_str = point.get("time", "")[:19]
                value = point.get("value", "N/A")
                print(f"    {time_str}: {value}")
            if len(graph_data) > 6:
                print("    ...")
            for point in graph_data[-3:]:
                time_str = point.get("time", "")[:19]
                value = point.get("value", "N/A")
                print(f"    {time_str}: {value}")
        else:
            print("  No graph data available")
    except MCPError as e:
        print(f"  Error: {e.message}")
    print()

    # Statistics
    print("Statistics (last 24 hours):")
    print("-" * 30)
    try:
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        stats_result = await client.call_tool("monitor-state", {
            "type": "stat",
            "id": monitor_id,
            "start": yesterday.isoformat(),
            "finish": now.isoformat()
        })

        stats = stats_result.data.get("stat", [])
        if stats and len(stats) > 0:
            stat = stats[0]  # Get first stat entry
            print(f"  Average: {stat.get('avg', 'N/A')}")
            print(f"  Minimum: {stat.get('min', 'N/A')}")
            print(f"  Maximum: {stat.get('max', 'N/A')}")
            print(f"  Availability: {stat.get('availability', 'N/A')}%")
        else:
            print("  No statistics available")
    except MCPError as e:
        print(f"  Error: {e.message}")


async def main():
    """Query monitor states."""
    print("=" * 60)
    print("IPNetwork MCP - Monitor State Query Example")
    print("=" * 60)
    print()

    # Check for monitor ID argument
    monitor_id = None
    if len(sys.argv) > 1:
        try:
            monitor_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid monitor ID: {sys.argv[1]}")
            sys.exit(1)

    client = IPNetworkMCPClient.from_env(verify_ssl=False)

    async with client:
        if monitor_id:
            await show_monitor_details(client, monitor_id)
        else:
            await show_all_monitors(client)
            print()
            print("Tip: Run with a monitor ID to see detailed information:")
            print("  python examples/04_monitor_state.py <monitor_id>")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(0)
