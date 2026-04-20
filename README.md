# SAP BTP Integration Suite MCP Server

This project provides a Python-based MCP server that connects to SAP BTP Integration Suite over the Cloud Integration OData API.

## Features

- OAuth2 client-credentials authentication
- MCP tools for connection checks, package discovery, artifact inspection, and message processing logs
- Simple project layout for continuing development in VS Code

## Implemented MCP Tools

- `ping_sap_btp`: Verifies the tenant is reachable and returns a small sample of packages.
- `list_integration_packages`: Lists integration packages from SAP Integration Suite.
- `list_artifacts`: Lists designtime artifacts, optionally filtered by package id.
- `get_artifact_details`: Reads a single integration artifact by id and version.
- `get_message_processing_logs`: Reads message processing logs with optional status and time filters.
- `get_custom_header_properties`: Reads custom header properties for a message processing log entry.

## Configuration

Copy `.env.example` to `.env` and set the values from your SAP BTP service key or API client configuration.

If your SAP BTP credentials come in the common JSON structure below, map them like this:

- `oauth.url` -> `SAP_BTP_BASE_URL`
- `oauth.tokenurl` -> `SAP_BTP_TOKEN_URL`
- `oauth.clientid` -> `SAP_BTP_CLIENT_ID`
- `oauth.clientsecret` -> `SAP_BTP_CLIENT_SECRET`

Some SAP service keys expose a runtime URL under `oauth.url` that can mint tokens but does not host the Cloud Integration OData API. If you see a `404 Not Found` mentioning `Requested route`, use the actual Integration Suite tenant API host for `SAP_BTP_BASE_URL` instead of the runtime route.

Required environment variables:

- `SAP_BTP_BASE_URL`
- `SAP_BTP_TOKEN_URL`
- `SAP_BTP_CLIENT_ID`
- `SAP_BTP_CLIENT_SECRET`

Optional:

- `SAP_BTP_API_PATH` defaults to `/api/v1`
- `SAP_BTP_TIMEOUT_SECONDS` defaults to `30`

## Run In VS Code

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
cp .env.example .env
btp-mcp
```

You can also run:

```bash
python -m btp_mcp.server
```

## MCP Client Example

Add the server to an MCP-capable client with a command similar to:

```json
{
  "mcpServers": {
    "sap-btp": {
      "command": "/absolute/path/to/btp-mcp/.venv/bin/python",
      "args": ["-m", "btp_mcp.server"],
      "cwd": "/absolute/path/to/btp-mcp"
    }
  }
}
```

## Notes

- SAP Cloud Integration OData APIs are exposed under `https://<host>/api/v1/...`
- For modifying requests, SAP requires a CSRF token. This starter currently focuses on read-oriented tools so it is safe to extend incrementally.
- JSON responses are requested with `$format=json` for easier MCP tool output handling.
- Use Python 3.10 or newer. Recent MCP server libraries no longer support Python 3.9.
