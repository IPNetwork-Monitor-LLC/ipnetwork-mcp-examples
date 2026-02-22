# Copyright (c) 2026 IPNetwork Monitor
# Licensed under the MIT License. See LICENSE file in the project root.
# This Python file uses the following encoding: utf-8
"""
IPNetwork MCP Client Wrapper

A reusable client for connecting to IPNetwork Monitor's MCP API.
For more information: https://ipnetwork-monitor.com/

Usage:
    async with IPNetworkMCPClient(url, token) as client:
        agents = await client.list_agents()
        print(agents)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MCPError(Exception):
    """Exception raised for MCP API errors."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


@dataclass
class MCPResult:
    """Result from an MCP API call."""
    data: dict[str, Any]
    warnings: list[str]

    @property
    def id(self) -> int | None:
        """Get the ID from a create operation result."""
        return self.data.get("id")


class TokenAuth(httpx.Auth):
    """Authentication handler for IPNetwork MCP API."""

    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


class IPNetworkMCPClient:
    """
    Client for IPNetwork Monitor MCP API.

    Args:
        url: The MCP server URL (e.g., "https://server:8888/mcp")
        token: Authentication token from IPNetwork MCP settings
        verify_ssl: Whether to verify SSL certificates (default: True)

    Example:
        async with IPNetworkMCPClient(url, token) as client:
            agents = await client.list_agents()
    """

    def __init__(self, url: str, token: str, verify_ssl: bool = True):
        self.url = url
        self.token = token
        self.verify_ssl = verify_ssl
        self._session: ClientSession | None = None
        self._context_stack: list[Any] = []

    @classmethod
    def from_env(cls, verify_ssl: bool = True) -> "IPNetworkMCPClient":
        """
        Create a client from environment variables.

        Requires MCP_URL and MCP_TOKEN environment variables.
        """
        url = os.environ.get("MCP_URL")
        token = os.environ.get("MCP_TOKEN")

        if not url or not token:
            raise ValueError(
                "MCP_URL and MCP_TOKEN environment variables are required.\n"
                "Example:\n"
                "  export MCP_URL=https://your-server:8888/mcp\n"
                "  export MCP_TOKEN=your-token-here"
            )

        return cls(url, token, verify_ssl)

    def _httpx_client_factory(self, **kwargs) -> httpx.AsyncClient:
        """Create an httpx client with optional SSL verification disabled."""
        return httpx.AsyncClient(verify=self.verify_ssl, **kwargs)

    async def __aenter__(self) -> "IPNetworkMCPClient":
        """Async context manager entry."""
        # Create the streamable HTTP client
        stream_context = streamablehttp_client(
            self.url,
            auth=TokenAuth(self.token),
            httpx_client_factory=self._httpx_client_factory
        )

        read_stream, write_stream, _ = await stream_context.__aenter__()
        self._context_stack.append(stream_context)

        # Create the MCP session
        session_context = ClientSession(read_stream, write_stream)
        self._session = await session_context.__aenter__()
        self._context_stack.append(session_context)

        # Initialize the connection
        await self._session.initialize()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close contexts in reverse order
        for ctx in reversed(self._context_stack):
            await ctx.__aexit__(exc_type, exc_val, exc_tb)
        self._context_stack.clear()
        self._session = None

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> MCPResult:
        """
        Call an MCP tool and return the result.

        Args:
            name: Tool name (e.g., "list-agents", "create-host")
            arguments: Tool arguments as a dictionary

        Returns:
            MCPResult with data and any warnings

        Raises:
            MCPError: If the API returns an error
        """
        if self._session is None:
            raise MCPError("Client not connected. Use 'async with' context manager.")

        response = await self._session.call_tool(name, arguments or {})

        if response.isError:
            error_text = response.content[0].text if response.content else "Unknown error"
            raise MCPError(error_text)

        result = json.loads(response.content[0].text)

        # Extract warnings if present
        warnings = result.pop("errors", []) if isinstance(result, dict) else []

        return MCPResult(data=result, warnings=warnings)

    # ==================== Convenience Methods ====================

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all monitoring agents."""
        result = await self.call_tool("list-agents")
        return result.data.get("agents", [])

    async def find_agent(self, name: str) -> dict[str, Any] | None:
        """Find an agent by name."""
        agents = await self.list_agents()
        return next((a for a in agents if a["name"] == name), None)

    async def list_children(
        self,
        parent_type: str,
        parent_id: int,
        plain: bool = False
    ) -> dict[str, Any]:
        """List children of an object."""
        result = await self.call_tool("list-children", {
            "type": parent_type,
            "id": parent_id,
            "plain": plain
        })
        return result.data

    async def find_hostgroup(self, parent_type: str, parent_id: int, name: str) -> dict[str, Any] | None:
        """Find a host group by name within a parent."""
        children = await self.list_children(parent_type, parent_id, plain=True)
        hostgroups = children.get("hostGroups", [])
        return next((hg for hg in hostgroups if hg["name"] == name), None)

    async def create_host(
        self,
        parent_id: int,
        name: str,
        host_def: dict[str, str],
        icon: str | None = None,
        admin_url: str | None = None
    ) -> MCPResult:
        """
        Create a new host.

        Args:
            parent_id: ID of the parent host group
            name: Host display name
            host_def: Host definition - either {"ip": "x.x.x.x"} or {"name": "hostname"}
            icon: Optional icon filename (e.g., "OS/Linux.png")
            admin_url: Optional admin web interface URL
        """
        config: dict[str, Any] = {"hostDef": host_def}
        if icon:
            config["hostIcon"] = icon
        if admin_url:
            config["adminWebInterface"] = admin_url

        return await self.call_tool("create-host", {
            "parentId": parent_id,
            "name": name,
            "config": config
        })

    async def create_monitor(
        self,
        host_id: int,
        name: str,
        monitor_type: str,
        config: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        activity: str = "active"
    ) -> MCPResult:
        """
        Create a new monitor on a host.

        Args:
            host_id: ID of the parent host
            name: Monitor display name
            monitor_type: Type of monitor (e.g., "ping", "http", "snmp")
            config: Monitor-specific configuration
            settings: Inheritable settings (polling interval, alerting, etc.)
            activity: Initial activity state ("active", "stopped")
        """
        return await self.call_tool("create-monitor", {
            "parentType": "host",
            "parentId": host_id,
            "name": name,
            "type": monitor_type,
            "activity": activity,
            "config": config or {},
            "settings": settings or {}
        })

    async def get_monitor_state(self, monitor_id: int) -> dict[str, Any]:
        """Get the current state of a monitor."""
        result = await self.call_tool("monitor-state", {
            "type": "current",
            "id": monitor_id
        })
        return result.data

    async def get_monitor_history(
        self,
        monitor_id: int,
        start: str,
        finish: str
    ) -> list[dict[str, Any]]:
        """
        Get state change history for a monitor.

        Args:
            monitor_id: Monitor ID
            start: Start time in ISO 8601 format
            finish: End time in ISO 8601 format
        """
        result = await self.call_tool("monitor-state", {
            "type": "history",
            "id": monitor_id,
            "start": start,
            "finish": finish
        })
        return result.data.get("history", [])

    async def list_alerts(self) -> list[dict[str, Any]]:
        """List all composite alerts."""
        result = await self.call_tool("list-alerts")
        return result.data.get("alerts", [])

    async def list_simple_actions(self) -> list[dict[str, Any]]:
        """List all simple actions."""
        result = await self.call_tool("list-simple-actions")
        return result.data.get("actions", [])

    async def list_alerting_rules(self) -> list[dict[str, Any]]:
        """List all alerting rules."""
        result = await self.call_tool("list-alerting-rules")
        return result.data.get("rules", [])

    async def list_schedules(self) -> list[dict[str, Any]]:
        """List all schedules."""
        result = await self.call_tool("list-schedules")
        return result.data.get("schedules", [])
