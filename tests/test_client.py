from btp_mcp.client import _unwrap_odata


def test_unwrap_odata_results_list() -> None:
    payload = {"d": {"results": [{"Id": "A"}]}}
    assert _unwrap_odata(payload) == [{"Id": "A"}]


def test_unwrap_odata_single_entity() -> None:
    payload = {"d": {"Id": "A", "Name": "Example"}}
    assert _unwrap_odata(payload) == {"Id": "A", "Name": "Example"}
