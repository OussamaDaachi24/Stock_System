import uuid

from tests.conftest import auth_headers


def _product(**overrides):
    base = {
        "sku": "SKU-001",
        "name": "Widget A",
        "barcode": "1234567890",
        "unit_of_measure": "piece",
        "category": "tools",
        "cost_price": "5.00",
        "sell_price": "10.00",
        "reorder_threshold": 10,
    }
    base.update(overrides)
    return base


def test_create_product_as_manager(client, manager_token):
    r = client.post("/api/v1/products", headers=auth_headers(manager_token), json=_product())
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["sku"] == "SKU-001"


def test_operator_cannot_create_product(client, operator_token):
    r = client.post("/api/v1/products", headers=auth_headers(operator_token), json=_product())
    assert r.status_code == 403


def test_duplicate_sku_rejected(client, admin_token):
    h = auth_headers(admin_token)
    assert client.post("/api/v1/products", headers=h, json=_product()).status_code == 201
    r = client.post("/api/v1/products", headers=h, json=_product(barcode="9999"))
    assert r.status_code == 409


def test_duplicate_barcode_rejected(client, admin_token):
    h = auth_headers(admin_token)
    assert client.post("/api/v1/products", headers=h, json=_product()).status_code == 201
    r = client.post("/api/v1/products", headers=h, json=_product(sku="SKU-002"))
    assert r.status_code == 409


def test_invalid_uom_rejected(client, admin_token):
    r = client.post(
        "/api/v1/products",
        headers=auth_headers(admin_token),
        json=_product(unit_of_measure="parsec"),
    )
    assert r.status_code == 400


def test_list_and_search(client, admin_token):
    h = auth_headers(admin_token)
    client.post("/api/v1/products", headers=h, json=_product(sku="A1", barcode="b1", name="Hammer"))
    client.post("/api/v1/products", headers=h, json=_product(sku="A2", barcode="b2", name="Screwdriver"))
    client.post("/api/v1/products", headers=h, json=_product(sku="A3", barcode="b3", name="Wrench"))

    r = client.get("/api/v1/products?search=hamm", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1
    assert r.json()["data"]["items"][0]["name"] == "Hammer"

    r = client.get("/api/v1/products?limit=2&offset=0", headers=h)
    assert r.status_code == 200
    assert len(r.json()["data"]["items"]) == 2


def test_update_captures_audit(client, admin_token, db):
    h = auth_headers(admin_token)
    create = client.post("/api/v1/products", headers=h, json=_product()).json()["data"]
    pid = create["product_id"]

    r = client.put(f"/api/v1/products/{pid}", headers=h, json={"name": "Widget A v2", "category": "new-cat"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Widget A v2"

    from app.models import AuditLog
    logs = db.query(AuditLog).filter(AuditLog.entity_type == "product", AuditLog.entity_id == pid).all()
    actions = {l.action for l in logs}
    assert "create" in actions and "update" in actions
    upd = next(l for l in logs if l.action == "update")
    assert upd.old_value["name"] == "Widget A"
    assert upd.new_value["name"] == "Widget A v2"


def test_idempotency_same_key_returns_same_product(client, admin_token):
    h = auth_headers(admin_token)
    key = str(uuid.uuid4())
    headers = {**h, "Idempotency-Key": key}
    r1 = client.post("/api/v1/products", headers=headers, json=_product())
    r2 = client.post("/api/v1/products", headers=headers, json=_product())
    assert r1.status_code == 201
    assert r2.status_code == 200  # cached response replayed
    assert r1.json()["data"]["product_id"] == r2.json()["data"]["product_id"]


def test_get_404(client, admin_token):
    r = client.get("/api/v1/products/9999", headers=auth_headers(admin_token))
    assert r.status_code == 404
