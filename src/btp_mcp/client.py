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
        response.raise_for_status()
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
        resource = (
            "MessageProcessingLogs"
            f"('{quote(message_guid, safe='')}')/CustomHeaderProperties"
        )
        return self._request("GET", resource)
