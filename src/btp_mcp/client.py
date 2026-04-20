from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from btp_mcp.config import Settings


def _strip_trailing_slash(value: str) -> str:
    return value[:-1] if value.endswith("/") else value


def _unwrap_odata(payload: Dict[str, Any]) -> Any:
    data = payload.get("d", payload)
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def _build_http_error_message(
    response: httpx.Response,
    *,
    base_url: str,
    resource_path: str,
) -> str:
    body = response.text.strip()

    if response.status_code == 404 and "Requested route" in body:
        return (
            "SAP BTP base URL does not expose the Integration Suite OData API. "
            f"Configured base URL: {base_url}. Requested resource: {resource_path}. "
            "This usually means the service key's runtime URL was used instead of the "
            "Cloud Integration tenant API host."
        )

    if response.status_code in (401, 403):
        return (
            "SAP BTP request was rejected. Verify the client credentials and ensure the "
            "service key or API client has permissions for the requested Integration Suite API."
        )

    return (
        f"SAP BTP request failed with HTTP {response.status_code} for resource "
        f"{resource_path}: {body[:300]}"
    )


@dataclass
class SapBtpClient:
    settings: Settings

    def __post_init__(self) -> None:
        self.base_url = _strip_trailing_slash(self.settings.sap_btp_base_url)
        self.api_path = self.settings.sap_btp_api_path
        if not self.api_path.startswith("/"):
            self.api_path = f"/{self.api_path}"

    def _get_token(self) -> str:
        response = httpx.post(
            self.settings.sap_btp_token_url,
            data={"grant_type": "client_credentials"},
            auth=(self.settings.sap_btp_client_id, self.settings.sap_btp_client_secret),
            timeout=self.settings.sap_btp_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise ValueError("SAP OAuth token response did not include access_token")
        return token

    def _request(
        self,
        method: str,
        resource_path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        token = self._get_token()
        url = f"{self.base_url}{self.api_path}/{resource_path.lstrip('/')}"
        query_params = {"$format": "json"}
        if params:
            query_params.update({k: v for k, v in params.items() if v is not None})

        response = httpx.request(
            method,
            url,
            params=query_params,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=self.settings.sap_btp_timeout_seconds,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                _build_http_error_message(
                    exc.response,
                    base_url=self.base_url,
                    resource_path=resource_path,
                )
            ) from exc
        return _unwrap_odata(response.json())

    def ping(self) -> Dict[str, Any]:
        packages = self.list_integration_packages(top=3)
        return {
            "base_url": self.base_url,
            "api_path": self.api_path,
            "package_sample_count": len(packages),
            "package_sample": packages,
        }

    def list_integration_packages(self, top: int = 25, skip: int = 0) -> Any:
        """List all integration packages.
        
        Returns package details including:
        - Id: Unique package identifier
        - Name: Display name of the package
        - Description: Package description
        - CreatedDate: When the package was created
        - ModifiedDate: Last modification timestamp
        - Vendor: Package vendor/creator
        
        Args:
            top: Maximum number of packages to return (default 25)
            skip: Number of packages to skip for pagination
            
        Returns:
            List of package objects with metadata and configuration details.
            
        Note:
            Requires design-time API permissions (IntegrationPackages read access).
        """
        return self._request(
            "GET",
            "IntegrationPackages",
            params={"$top": top, "$skip": skip},
        )

    def list_artifacts(
        self,
        top: int = 50,
        skip: int = 0,
        package_id: Optional[str] = None,
    ) -> Any:
        """List integration artifacts (iflows, mappings, scripts, etc.).
        
        Returns artifact details including:
        - Id: Unique artifact identifier (iflow ID)
        - Name: Display name of the integration flow
        - ArtifactType: Type of artifact (IntegrationFlow, MessageMapping, Script, etc.)
        - PackageId: ID of the package containing this artifact
        - PackageName: Name of the containing package
        - Description: Artifact description
        - CreatedDate: Creation timestamp
        - ModifiedDate: Last modification timestamp
        - Version: Current version of the artifact
        - DeployedVersion: Version currently deployed (if deployed)
        - Status: Current deployment status (Active, InActive, Draft)
        - RuntimeStatus: Whether the artifact is active in runtime
        
        Args:
            top: Maximum number of artifacts to return (default 50)
            skip: Number of artifacts to skip for pagination
            package_id: Optional filter to get artifacts from specific package
            
        Returns:
            List of artifact objects with design-time metadata and configuration.
            
        Note:
            Requires design-time API permissions (IntegrationDesigntimeArtifacts read access).
        """
        params: Dict[str, Any] = {"$top": top, "$skip": skip}
        if package_id:
            params["$filter"] = f"PackageId eq '{package_id}'"
        return self._request("GET", "IntegrationDesigntimeArtifacts", params=params)

    def get_artifact_details(self, artifact_id: str, version: str = "active") -> Any:
        resource = (
            f"IntegrationDesigntimeArtifacts(Id='{quote(artifact_id, safe='')}',"
            f"Version='{quote(version, safe='')}')"
        )
        return self._request("GET", resource)

    def get_message_processing_logs(
        self,
        status: Optional[str] = None,
        started_after: Optional[str] = None,
        ended_before: Optional[str] = None,
        top: int = 100,
        skip: int = 0,
    ) -> Any:
        """Get message processing logs for executed integration flows.
        
        Each log entry contains runtime information including:
        - MessageGuid: Unique identifier for the processed message
        - LogStart: When processing started (ISO-like timestamp)
        - LogEnd: When processing ended
        - Status: Processing status (COMPLETED, FAILED, ERROR, DISCARDED, RETRY_EXHAUSTED)
        - DurationInMs: How long processing took
        - IntegrationArtifact: Nested object with iflow details:
          * Id: Integration flow unique identifier
          * Name: Integration flow display name
          * Type: Always "INTEGRATION_FLOW" for iflows
          * PackageId: ID of the package containing this iflow
          * PackageName: Name of the package
        - ErrorInformation: Details if status is FAILED or ERROR
        - CustomHeaderProperties: Custom headers from the message
        - Receiver: Target system name
        - Sender: Source system name
        
        Args:
            status: Filter by message status (COMPLETED, FAILED, ERROR, DISCARDED, etc.)
            started_after: Filter messages processed after this timestamp (ISO format)
            ended_before: Filter messages processed before this timestamp
            top: Maximum number of logs to return (default 100, max 2000)
            skip: Number of logs to skip for pagination
            
        Returns:
            List of message processing log entries with runtime execution data.
            Each entry includes embedded IntegrationArtifact with iflow and package info.
            
        Note:
            - Requires runtime monitoring API permissions (MessageProcessingLogs read access)
            - This is the primary method to discover active iflows with recent message activity
            - Only iflows that have processed messages appear in these logs
        """
        filters = []
        if status:
            filters.append(f"Status eq '{status.upper()}'")
        if started_after:
            filters.append(f"LogStart gt datetime'{started_after}'")
        if ended_before:
            filters.append(f"LogEnd lt datetime'{ended_before}'")

        params: Dict[str, Any] = {"$top": top, "$skip": skip}
        if filters:
            params["$filter"] = " and ".join(filters)

        return self._request("GET", "MessageProcessingLogs", params=params)

    def get_custom_header_properties(self, message_guid: str) -> Any:
        """Get custom header properties for a specific processed message.
        
        Retrieves custom headers and properties associated with a message
        processing log entry, useful for understanding message metadata
        and flow-specific properties.
        
        Args:
            message_guid: The MessageGuid from a message processing log entry
            
        Returns:
            Dictionary containing custom header properties for the message.
            
        Note:
            Requires runtime monitoring API permissions.
        """
        resource = (
            "MessageProcessingLogs"
            f"('{quote(message_guid, safe='')}')/CustomHeaderProperties"
        )
        return self._request("GET", resource)
