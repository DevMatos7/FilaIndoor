def test_toledo_status_disabled_forces_native(client):
    st = client.get("/api/v1/toledo/status")
    assert st.status_code == 200
    body = st.json()
    assert body["toledo_enabled"] is False
    assert body["effective_mode"] == "NATIVE"
    assert body["adapter_implemented"] is True  # S14 scaffold; flag off → NATIVE
    assert body["discovery_only"] is False


def test_toledo_discovery_crud(client, auth_header):
    get1 = client.get("/api/v1/toledo/discovery", headers=auth_header)
    assert get1.status_code == 200, get1.text
    assert "completeness" in get1.json()

    put = client.put(
        "/api/v1/toledo/discovery",
        json={
            "mgv_version": "MGV-TEST",
            "mit_version": "MIT-5",
            "mit_cloud": True,
            "api_enabled": False,
            "players_notes": "2 players loja demo",
            "docs_compared": True,
            "mode_intent": "TOLEDO_DISPLAY",
            "integration_key_configured": False,
        },
        headers=auth_header,
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["mgv_version"] == "MGV-TEST"
    assert body["mode_intent"] == "TOLEDO_DISPLAY"
    assert body["completeness"]["percent"] >= 80

    # status permanece NATIVE com flag off
    st = client.get("/api/v1/toledo/status")
    assert st.json()["effective_mode"] == "NATIVE"
