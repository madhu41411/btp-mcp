"""Entry point for the MCP SSE server (used by Render btp-mcp-sse service)."""
import os
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from btp_mcp.server import build_server


async def health(request):
    return JSONResponse({"status": "ok"})


mcp = build_server()
mcp_app = mcp.http_app(transport="sse")

app = Starlette(routes=[
    Route("/health", health),
    Mount("/", app=mcp_app),
])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
