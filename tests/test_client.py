import httpx

from btp_mcp.client import _build_http_error_message, _unwrap_odata


def test_unwrap_odata_results_list() -> None:
    payload = {"d": {"results": [{"Id": "A"}]}}
    assert _unwrap_odata(payload) == [{"Id": "A"}]


def test_unwrap_odata_single_entity() -> None:
    payload = {"d": {"Id": "A", "Name": "Example"}}
    assert _unwrap_odata(payload) == {"Id": "A", "Name": "Example"}


def test_build_http_error_message_for_route_not_found() -> None:
    request = httpx.Request("GET", "https://example.invalid/api/v1/IntegrationPackages")
    response = httpx.Response(
        404,
        request=request,
        text="404 Not Found: Requested route ('example.invalid') does not exist.",
    )

    message = _build_http_error_message(
        response,
        base_url="https://example.invalid",
        resource_path="IntegrationPackages",
    )

    assert "does not expose the Integration Suite OData API" in message
    assert "runtime URL was used" in message
