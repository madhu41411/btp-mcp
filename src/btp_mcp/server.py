from __future__ import annotations

from fastmcp import FastMCP

from btp_mcp.client import SapBtpClient
from btp_mcp.config import get_settings


def build_server() -> FastMCP:
    settings = get_settings()
    client = SapBtpClient(settings)
    mcp = FastMCP("sap-btp-integration-suite")

    @mcp.tool()
    def ping_sap_btp() -> dict:
        """Check SAP BTP connectivity and return a small package sample."""
        return client.ping()

    @mcp.tool()
    def list_integration_packages(top: int = 25, skip: int = 0) -> list[dict]:
        """List integration packages from SAP Integration Suite."""
        return client.list_integration_packages(top=top, skip=skip)

    @mcp.tool()
    def list_artifacts(
        package_id: str | None = None,
    ) -> list[dict]:
        """
        List all design-time integration flows (iflows) from SAP BTP Integration Suite.
        Iterates through all packages and fetches artifacts from each.
        Optionally filter by a specific package_id.
        Returns iflow Id, Name, PackageId, PackageName, Version, Description.
        """
        packages = client.list_integration_packages(top=200)
        iflows = []
        if not isinstance(packages, list):
            return iflows
        for pkg in packages:
            pkg_id = pkg.get("Id")
            pkg_name = pkg.get("Name")
            if not pkg_id:
                continue
            if package_id and pkg_id.lower() != package_id.lower():
                continue
            try:
                arts = client._request(
                    "GET",
                    f"IntegrationPackages('{pkg_id}')/IntegrationDesigntimeArtifacts",
                    params={"$top": 200},
                )
                if isinstance(arts, list):
                    for a in arts:
                        iflows.append({
                            "Id": a.get("Id"),
                            "Name": a.get("Name"),
                            "PackageId": pkg_id,
                            "PackageName": pkg_name,
                            "Version": a.get("Version"),
                            "Description": a.get("Description"),
                        })
            except Exception:
                pass
        return iflows

    @mcp.tool()
    def get_artifact_details(artifact_id: str, version: str = "active") -> dict:
        """Get a single artifact by id and version."""
        return client.get_artifact_details(artifact_id=artifact_id, version=version)

    @mcp.tool()
    def get_message_processing_logs(
        status: str | None = None,
        started_after: str | None = None,
        ended_before: str | None = None,
        top: int = 100,
        skip: int = 0,
    ) -> list[dict]:
        """
        Get message processing logs.

        Timestamps should be ISO-like values expected by SAP OData, for example
        2026-04-20T00:00:00
        """
        return client.get_message_processing_logs(
            status=status,
            started_after=started_after,
            ended_before=ended_before,
            top=top,
            skip=skip,
        )

    @mcp.tool()
    def get_custom_header_properties(message_guid: str) -> list[dict]:
        """Get custom header properties for a specific message processing log id."""
        return client.get_custom_header_properties(message_guid=message_guid)

    return mcp


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    server = build_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    elif args.transport == "sse":
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Mount, Route
        import uvicorn

        async def health(request):
            return JSONResponse({"status": "ok"})

        mcp_app = server.http_app(transport="sse")
        app = Starlette(routes=[
            Route("/health", health),
            Mount("/", app=mcp_app),
        ])
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        server.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
