# SAP BTP Integration Suite MCP Server

A tidy Python MCP server for SAP BTP Integration Suite that includes:
- a public HTTP API,
- a web UI at `/`,
- and a CLI helper for listing active integration flows.

## What this repository contains

- `http_server.py` — Flask HTTP server with UI and authenticated REST endpoints.
- `src/btp_mcp/client.py` — SAP BTP Integration Suite client.
- `src/btp_mcp/config.py` — environment-backed settings.
- `src/btp_mcp/server.py` — MCP server entrypoint for `btp-mcp` command and `python -m btp_mcp.server`.
- `list_iflows.py` — helper script to extract active iflows from runtime message logs.
- `templates/index.html` — browser interface for asking iflow questions.
- `Dockerfile`, `render.yaml` — deployment configuration for Render.

## Requirements

- Python 3.10+
- `pip install -e .`
- SAP BTP Integration Suite credentials with access to runtime `MessageProcessingLogs`

## Configuration

Copy `.env.example` to `.env` and set values:

- `SAP_BTP_BASE_URL`
- `SAP_BTP_TOKEN_URL`
- `SAP_BTP_CLIENT_ID`
- `SAP_BTP_CLIENT_SECRET`
- Optional: `SAP_BTP_API_PATH` (defaults to `/api/v1`)
- Optional: `SAP_BTP_TIMEOUT_SECONDS` (defaults to `30`)
- Optional: `API_KEY` for securing `/api/*` endpoints.

> Use the Integration Suite tenant API host for `SAP_BTP_BASE_URL`. If you receive a 404 mentioning `Requested route`, the runtime service URL is likely incorrect.

## Run the HTTP server locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python http_server.py
```

Then open:

```bash
http://localhost:8000/
```

## Available endpoints

- `GET /` — web UI homepage
- `GET /health` — health check
- `GET /api/ping` — BTP connectivity check
- `GET /api/packages` — list integration packages
- `GET /api/artifacts` — list artifacts
- `GET /api/logs` — message processing logs
- `POST /api/chat` — natural language query from UI

## Securing the API

If `API_KEY` is set, API routes require the HTTP header:

```bash
X-API-Key: <your-api-key>
```

The `/health` endpoint remains public.

## CLI helper

To list active iflows from recent runtime logs:

```bash
python list_iflows.py
```

## MCP server

Use the built-in MCP entrypoint when you need an MCP-compatible command:

```bash
python -m btp_mcp.server --transport stdio
```

or with the installed script:

```bash
btp-mcp
```

## Docker and Render deployment

Render is configured to run `http_server.py` on port `8000`.

The `render.yaml` and `Dockerfile` are ready for deployment.

## Clean workspace

This repository has been tidied by removing old duplicate launch scripts, generated files, and stale documentation.

## Notes

- Runtime logs only show iflows with recent activity. Full design-time artifact listing may require broader Integration Suite permissions.
- This project is intentionally focused on read-only discovery and monitoring.
