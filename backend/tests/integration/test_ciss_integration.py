from app.modules.integration.providers.ciss_api import CISSApiProvider
from app.modules.integration.providers.mock import MockERPProvider


def test_erp_provider_mock_and_no_writes():
    mock = MockERPProvider()
    assert mock.capabilities()["writes_forbidden"] is True
    products = mock.get_products()
    assert len(products) >= 3
    price = mock.get_price("SKU-PICANHA")
    assert price and price.promo_price == 59.9

    api = CISSApiProvider(base_url="", api_key="")
    assert api.configured is False
    assert api.get_products() == []


def test_sync_snapshot_offer_only_in_stock(client, auth_header, seeded):
    store_id = seeded["store"].id
    # garantir external_code para mock store mapping
    seeded["store"].external_code = "CAMPO_NOVO"
    seeded["db"].commit()

    ensure = client.post(
        "/api/v1/integrations",
        json={"store_id": store_id, "provider": "mock", "external_store_id": "CAMPO_NOVO"},
        headers=auth_header,
    )
    assert ensure.status_code == 200, ensure.text

    sync = client.post("/api/v1/integrations/sync", params={"store_id": store_id}, headers=auth_header)
    assert sync.status_code == 200, sync.text
    assert sync.json()["status"] == "SUCCESS"
    assert sync.json()["products_upserted"] >= 3

    snaps = client.get("/api/v1/integrations/snapshots", params={"store_id": store_id}, headers=auth_header)
    assert snaps.status_code == 200
    assert len(snaps.json()) >= 3

    offer_ok = client.post(
        "/api/v1/integrations/offers",
        json={
            "store_id": store_id,
            "name": "Oferta Picanha",
            "product_external_id": "SKU-PICANHA",
            "template_key": "oferta_acougue",
            "only_in_stock": True,
        },
        headers=auth_header,
    )
    assert offer_ok.status_code == 200, offer_ok.text
    rendered = client.get(f"/api/v1/integrations/offers/{offer_ok.json()['id']}/render", headers=auth_header)
    assert rendered.status_code == 200
    body = rendered.json()
    assert body["renderable"] is True
    assert "PICANHA" in body["offer"]["lines"][0]
    assert any("59" in line for line in body["offer"]["lines"])

    # linguica mock tem estoque 0 → ONLY_IN_STOCK bloqueia
    offer_oos = client.post(
        "/api/v1/integrations/offers",
        json={
            "store_id": store_id,
            "name": "Linguiça",
            "product_external_id": "SKU-LINGUICA",
            "only_in_stock": True,
            "min_stock_qty": 0.01,
        },
        headers=auth_header,
    )
    assert offer_oos.status_code == 200
    blocked = client.get(f"/api/v1/integrations/offers/{offer_oos.json()['id']}/render", headers=auth_header)
    assert blocked.json()["renderable"] is False
    assert blocked.json()["reason"] == "ONLY_IN_STOCK"

    active = client.get("/api/v1/integrations/offers/active", params={"store_id": store_id}, headers=auth_header)
    assert active.status_code == 200
    assert len(active.json()) >= 2


def test_provider_info_read_only(client, auth_header):
    info = client.get("/api/v1/integrations/provider", headers=auth_header)
    assert info.status_code == 200
    assert info.json()["writes_forbidden"] is True
    assert info.json()["read_only"] is True
