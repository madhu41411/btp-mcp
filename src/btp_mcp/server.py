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
        top: int = 50,
        skip: int = 0,
        package_id: str | None = None,
    ) -> list[dict]:
        """List designtime artifacts, optionally filtered by package id."""
        return client.list_artifacts(top=top, skip=skip, package_id=package_id)

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
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
