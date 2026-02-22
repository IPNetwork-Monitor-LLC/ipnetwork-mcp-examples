#!/usr/bin/env python3
# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
Example 03: Alerting Setup

Demonstrates how to set up a complete alerting pipeline:
- Create a simple action (email notification)
- Create a schedule (business hours)
- Create a composite alert (action + schedule)
- Create an alerting rule

For more information: https://ipnetwork-monitor.com/

Usage:
    export MCP_URL="https://your-server:8888/mcp"
    export MCP_TOKEN="your-token"
    python examples/03_alerting_setup.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_client import IPNetworkMCPClient, MCPError


# Configuration - modify these values as needed
EMAIL_RECIPIENT = "admin@example.com"
SMTP_SERVER = "smtp.example.com"


async def main():
    """Set up alerting configuration."""
    print("=" * 60)
    print("IPNetwork MCP - Alerting Setup Example")
    print("=" * 60)
    print()

    client = IPNetworkMCPClient.from_env(verify_ssl=False)

    async with client:
        # Step 1: List existing alerts and actions
        print("[Info] Existing configuration:")
        actions = await client.list_simple_actions()
        alerts = await client.list_alerts()
        rules = await client.list_alerting_rules()
        schedules = await client.list_schedules()

        print(f"       Simple Actions: {len(actions)}")
        print(f"       Composite Alerts: {len(alerts)}")
        print(f"       Alerting Rules: {len(rules)}")
        print(f"       Schedules: {len(schedules)}")
        print()

        # Step 2: Create a simple email action
        print("[1/4] Creating email action...")
        try:
            action_result = await client.call_tool("create-simple-action", {
                "name": "Email to Admin",
                "type": "Send mail",
                "config": {
                    "To": EMAIL_RECIPIENT,
                    "Subject": "$HostName - $MonitorName is $MonitorState",
                    "Content": """Alert Notification

Host: $HostName ($HostIP)
Monitor: $MonitorName
State: $MonitorState
Time: $DateTime

Last Value: $MonitorValue $MonitorMeasure

---
Sent by IPNetwork Monitor
"""
                }
            })
            action_id = action_result.id
            print(f"       Created action ID: {action_id}")
        except MCPError as e:
            print(f"       Error: {e.message}")
            sys.exit(1)

        # Step 3: Create a business hours schedule
        print("[2/4] Creating business hours schedule...")
        try:
            schedule_result = await client.call_tool("create-schedule", {
                "name": "Business Hours",
                "config": {
                    "mon": "09:00-18:00",
                    "tue": "09:00-18:00",
                    "wed": "09:00-18:00",
                    "thu": "09:00-18:00",
                    "fri": "09:00-17:00",
                    "sat": "",
                    "sun": ""
                }
            })
            schedule_id = schedule_result.id
            print(f"       Created schedule ID: {schedule_id}")
        except MCPError as e:
            print(f"       Error: {e.message}")
            sys.exit(1)

        # Step 4: Create a composite alert combining action and schedule
        print("[3/4] Creating composite alert...")
        try:
            alert_result = await client.call_tool("create-alert", {
                "name": "Business Hours Email Alert",
                "config": {
                    "actions": [
                        {
                            "action": action_id,
                            "schedule": schedule_id
                        }
                    ]
                }
            })
            alert_id = alert_result.id
            print(f"       Created alert ID: {alert_id}")
        except MCPError as e:
            print(f"       Error: {e.message}")
            sys.exit(1)

        # Step 5: Create an alerting rule
        print("[4/4] Creating alerting rule...")
        try:
            rule_result = await client.call_tool("create-alerting-rule", {
                "name": "Standard Alerting Rule",
                "config": {
                    "down": {
                        "enter": {
                            "alert": alert_id,
                            "delaySec": 60,  # Wait 60 seconds before alerting
                            "recoveryAlert": alert_id
                        },
                        "extended": {
                            "alert": alert_id,
                            "delayMin": 30,   # After 30 minutes
                            "repeatMin": 60,  # Repeat every hour
                            "recoveryAlert": alert_id
                        }
                    },
                    "warning": {
                        "enter": {
                            "alert": alert_id,
                            "delaySec": 120,  # Wait 2 minutes for warnings
                            "recoveryAlert": alert_id
                        }
                    }
                }
            })
            rule_id = rule_result.id
            print(f"       Created rule ID: {rule_id}")
        except MCPError as e:
            print(f"       Error: {e.message}")
            sys.exit(1)

        print()
        print("=" * 60)
        print("Alerting setup completed!")
        print("=" * 60)
        print()
        print("Created resources:")
        print(f"  - Simple Action 'Email to Admin' (ID: {action_id})")
        print(f"  - Schedule 'Business Hours' (ID: {schedule_id})")
        print(f"  - Composite Alert 'Business Hours Email Alert' (ID: {alert_id})")
        print(f"  - Alerting Rule 'Standard Alerting Rule' (ID: {rule_id})")
        print()
        print("To apply this alerting rule to monitors, set the 'alerting.rule'")
        print(f"setting to {rule_id} on a host group, host, or individual monitor.")
        print()
        print("Example using settings inheritance on a host group:")
        print("""
    await client.call_tool("create-hostgroup", {
        "parentType": "agent",
        "parentId": agent_id,
        "name": "Monitored Servers",
        "config": {},
        "settings": {
            "alerting": {
                "rule": """ + str(rule_id) + """
            }
        }
    })
""")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(0)
