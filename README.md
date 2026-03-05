# IPNetwork MCP Client Examples

Python examples demonstrating how to use the [IPNetwork Monitor](https://ipnetwork-monitor.com/) MCP (Model Context Protocol) API for network monitoring automation.

## Overview

[IPNetwork Monitor](https://ipnetwork-monitor.com/) is a comprehensive network monitoring solution that provides an MCP API for programmatic access to monitoring configuration and data. This repository contains example scripts showing how to:

- Connect to the IPNetwork MCP server
- Create and manage hosts and host groups
- Configure various monitor types (Ping, HTTP, SNMP, etc.)
- Set up alerting rules and notifications
- Query monitor states and statistics

## Prerequisites

- Python 3.10 or higher
- IPNetwork Monitor with MCP enabled
- MCP authentication token (read-write for configuration changes)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/IPNetwork-Monitor-LLC/ipnetwork-mcp-examples.git
cd ipnetwork-mcp-examples
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Set the following environment variables before running the examples:

| Variable | Description | Example |
|----------|-------------|---------|
| `MCP_URL` | URL of the IPNetwork MCP endpoint | `https://your-server:8888/mcp` |
| `MCP_TOKEN` | Authentication token (from IPNetwork MCP settings) | `7954AAA9-B736-4FD7-B10D-255C0FDF030D` |

### Linux/macOS

```bash
export MCP_URL="https://your-ipnetwork-server:8888/mcp"
export MCP_TOKEN="your-token-here"
```

### Windows (Command Prompt)

```cmd
set MCP_URL=https://your-ipnetwork-server:8888/mcp
set MCP_TOKEN=your-token-here
```

### Windows (PowerShell)

```powershell
$env:MCP_URL = "https://your-ipnetwork-server:8888/mcp"
$env:MCP_TOKEN = "your-token-here"
```

## Project Structure

```
ipnetwork-mcp-examples/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── LICENSE                   # MIT License
├── .gitignore               # Git ignore rules
├── src/
│   ├── __init__.py
│   └── mcp_client.py        # Reusable MCP client wrapper
└── examples/
    ├── 01_basic_connection.py    # Basic connection example
    ├── 02_create_host.py         # Create hosts and monitors
    ├── 03_alerting_setup.py      # Configure alerting
    ├── 04_monitor_state.py       # Query monitor states
    ├── 05_bulk_operations.py     # Bulk configuration example
    └── 06_check_monitor_status.py # Check specific monitor status
```

## Examples

### Quick Start

Run the basic connection example to verify your setup:

```bash
python examples/01_basic_connection.py
```

### Example Descriptions

| Example | Description |
|---------|-------------|
| `01_basic_connection.py` | Connect to MCP server and list available agents |
| `02_create_host.py` | Create a host with Ping and HTTP monitors |
| `03_alerting_setup.py` | Set up email alerts and alerting rules |
| `04_monitor_state.py` | Query current state and historical data |
| `05_bulk_operations.py` | Bulk create multiple hosts from a list |
| `06_check_monitor_status.py` | Check status of a specific monitor by name, qualified name, or ID |

## SSL/TLS Certificates

By default, IPNetwork Monitor uses a self-signed certificate. The examples include an option to disable certificate verification for testing. **For production use**, you should either:

1. Install a valid SSL certificate on your IPNetwork Monitor server
2. Add the self-signed certificate to your system's trusted store

To disable certificate verification (testing only):

```python
from src.mcp_client import IPNetworkMCPClient

async with IPNetworkMCPClient(url, token, verify_ssl=False) as client:
    # Your code here
```

## API Reference

For complete API documentation, see:
- [IPNetwork MCP Documentation](https://ipnetwork-monitor.com/help/mcp-api-reference-manual.html)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

### Common Operations

#### List Agents

```python
agents = await client.call_tool("list-agents")
```

#### Create Host

```python
host = await client.call_tool("create-host", {
    "parentId": hostgroup_id,
    "name": "My Server",
    "config": {
        "hostDef": {"ip": "192.168.1.100"}
    }
})
```

#### Create Monitor

```python
monitor = await client.call_tool("create-monitor", {
    "parentType": "host",
    "parentId": host_id,
    "name": "HTTPS Check",
    "type": "http",
    "config": {
        "URL": "https://example.com/health"
    }
})
```

#### Get Monitor State

```python
state = await client.call_tool("monitor-state", {
    "type": "current",
    "id": monitor_id
})
```

#### Check Specific Monitor Status

Look up a monitor by ID, name, or qualified name and display its current state:

```bash
# By monitor ID
python examples/06_check_monitor_status.py 27

# By monitor name (case-insensitive search across all agents)
python examples/06_check_monitor_status.py "HTTP(S)"

# By qualified name: "<Monitor name> on <Host name>"
python examples/06_check_monitor_status.py "Ping Check on Test Host"
```

When using a plain monitor name, if multiple monitors share the same name across
different hosts, the script lists all matches and asks you to re-run with a
specific ID or a qualified name. The qualified name format
`"<Monitor name> on <Host name>"` disambiguates by restricting the search to the
specified host.

Exit codes: `0` = ok, `1` = warning or not found, `2` = down.

## Error Handling

All examples include proper error handling. The MCP client wrapper provides structured error responses:

```python
try:
    result = await client.call_tool("get-host", {"id": 999})
except MCPError as e:
    print(f"MCP Error: {e.message}")
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## Support

- **Product Website**: [https://ipnetwork-monitor.com/](https://ipnetwork-monitor.com/)
- **Issues**: Use the [GitHub issue tracker](https://github.com/IPNetwork-Monitor-LLC/ipnetwork-mcp-examples/issues) for bug reports and feature requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [IPNetwork Monitor](https://ipnetwork-monitor.com/) - Network monitoring solution
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) - Protocol specification
