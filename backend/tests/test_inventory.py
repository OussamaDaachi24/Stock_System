from tests.conftest import auth_headers


def _make_product(client, token, sku="P-1", barcode=None, **extra):
    payload = {
        "sku": sku,
        "name": f"Product {sku}",
        "unit_of_measure": "piece",
        "barcode": barcode,
        **extra,
    }
    r = client.post("/api/v1/products", headers=auth_headers(token), json=payload)
    assert r.status_code == 201, r.text
    return r.json()["data"]


# --- Adjustment / ledger ---
def test_adjustment_creates_ledger_and_updates_snapshot(client, admin_token):
    p = _make_product(client, admin_token, sku="ADJ-1")
    pid = p["product_id"]

    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": pid, "quantity_delta": 25, "reason": "Initial stock", "allow_negative": True},
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["on_hand"] == 25
    assert data["available"] == 25
    assert data["ledger_id"] > 0

    r = client.get(f"/api/v1/inventory/snapshot?product_id={pid}", headers=auth_headers(admin_token))
    assert r.status_code == 200
    snap = r.json()["data"]
    assert snap["on_hand"] == 25
    assert snap["available"] == 25

    r = client.get(f"/api/v1/inventory/ledger?product_id={pid}", headers=auth_headers(admin_token))
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["type"] == "adjustment"
    assert items[0]["quantity_delta"] == 25


def test_adjustment_blocks_negative_stock_by_default(client, admin_token):
    p = _make_product(client, admin_token, sku="ADJ-NEG")
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": -5, "reason": "Lost"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["message"]["code"] == "NEGATIVE_STOCK_NOT_ALLOWED"


def test_adjustment_allow_negative_overrides(client, admin_token):
    p = _make_product(client, admin_token, sku="ADJ-NEG2")
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={
            "product_id": p["product_id"],
            "quantity_delta": -3,
            "reason": "Backorder policy",
            "allow_negative": True,
        },
    )
    assert r.status_code == 201
    assert r.json()["data"]["on_hand"] == -3


def test_adjustment_zero_rejected(client, admin_token):
    p = _make_product(client, admin_token, sku="ADJ-Z")
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": 0, "reason": "x"},
    )
    assert r.status_code == 400


def test_operator_cannot_adjust(client, admin_token, operator_token):
    p = _make_product(client, admin_token, sku="ADJ-ROLE")
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(operator_token),
        json={"product_id": p["product_id"], "quantity_delta": 5, "reason": "test", "allow_negative": True},
    )
    assert r.status_code == 403


# --- Immutability ---
def test_ledger_is_immutable(client, admin_token, db):
    p = _make_product(client, admin_token, sku="IMM-1")
    client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": 10, "reason": "init", "allow_negative": True},
    )
    from app.models import InventoryLedger
    entry = db.query(InventoryLedger).first()
    original_qty = entry.quantity_delta

    # Even if attempted at the ORM layer, callers must never mutate; we don't
    # rely on a DB trigger (sqlite doesn't have one) but we verify our
    # service-layer contract: there is no update path. Confirm by ensuring
    # subsequent corrections require a new ledger row.
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": -2, "reason": "correction", "allow_negative": True},
    )
    assert r.status_code == 201
    rows = db.query(InventoryLedger).filter_by(product_id=p["product_id"]).all()
    assert len(rows) == 2
    assert rows[0].quantity_delta == original_qty


# --- Reconciliation ---
def test_reconcile_detects_and_corrects_drift(client, admin_token, db):
    p = _make_product(client, admin_token, sku="REC-1")
    client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": 50, "reason": "init", "allow_negative": True},
    )

    from app.models import StockSnapshot
    snap = db.query(StockSnapshot).filter_by(product_id=p["product_id"]).first()
    snap.on_hand = 999
    snap.available = 999
    db.commit()

    r = client.post("/api/v1/inventory/reconcile", headers=auth_headers(admin_token))
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["mismatches_found"] == 1
    assert body["corrected"][0]["product_id"] == p["product_id"]
    assert body["corrected"][0]["after"]["on_hand"] == 50

    db.refresh(snap)
    assert snap.on_hand == 50


# --- Low stock ---
def test_low_stock_query(client, admin_token):
    p1 = _make_product(client, admin_token, sku="LS-1", reorder_threshold=10)
    p2 = _make_product(client, admin_token, sku="LS-2", reorder_threshold=5)

    client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p1["product_id"], "quantity_delta": 3, "reason": "init", "allow_negative": True},
    )
    client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p2["product_id"], "quantity_delta": 20, "reason": "init", "allow_negative": True},
    )

    r = client.get("/api/v1/inventory/low-stock", headers=auth_headers(admin_token))
    assert r.status_code == 200
    rows = r.json()["data"]
    skus = {row["sku"] for row in rows}
    assert "LS-1" in skus
    assert "LS-2" not in skus


def test_low_stock_dedupes_per_day(client, admin_token, db):
    p = _make_product(client, admin_token, sku="LSA-1", reorder_threshold=10)
    client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": 1, "reason": "init", "allow_negative": True},
    )
    client.get("/api/v1/inventory/low-stock?raise_alerts=true", headers=auth_headers(admin_token))
    client.get("/api/v1/inventory/low-stock?raise_alerts=true", headers=auth_headers(admin_token))

    from app.models import LowStockAlert
    rows = db.query(LowStockAlert).filter_by(product_id=p["product_id"]).all()
    assert len(rows) == 1


# --- Snapshot bootstrapping ---
def test_snapshot_auto_created_for_product_without_movements(client, admin_token):
    p = _make_product(client, admin_token, sku="SNP-NEW")
    r = client.get(f"/api/v1/inventory/snapshot?product_id={p['product_id']}", headers=auth_headers(admin_token))
    assert r.status_code == 200
    snap = r.json()["data"]
    assert snap["on_hand"] == 0
    assert snap["available"] == 0


def test_snapshot_404_for_unknown_product(client, admin_token):
    r = client.get("/api/v1/inventory/snapshot?product_id=999999", headers=auth_headers(admin_token))
    assert r.status_code == 404


# --- Idempotency on adjustments ---
def test_adjustment_idempotent(client, admin_token):
    import uuid
    p = _make_product(client, admin_token, sku="IDEM-ADJ")
    key = str(uuid.uuid4())
    headers = {**auth_headers(admin_token), "Idempotency-Key": key}
    body = {"product_id": p["product_id"], "quantity_delta": 7, "reason": "init", "allow_negative": True}

    r1 = client.post("/api/v1/inventory/adjustments", headers=headers, json=body)
    r2 = client.post("/api/v1/inventory/adjustments", headers=headers, json=body)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["data"]["ledger_id"] == r2.json()["data"]["ledger_id"]

    r = client.get(f"/api/v1/inventory/ledger?product_id={p['product_id']}", headers=auth_headers(admin_token))
    assert r.json()["data"]["total"] == 1


# --- Filtering ---
def test_ledger_filter_by_type(client, admin_token):
    p = _make_product(client, admin_token, sku="FLT-1")
    client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity_delta": 5, "reason": "x", "allow_negative": True},
    )
    r = client.get(
        f"/api/v1/inventory/ledger?product_id={p['product_id']}&type=adjustment",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1

    r = client.get(
        f"/api/v1/inventory/ledger?product_id={p['product_id']}&type=receiving",
        headers=auth_headers(admin_token),
    )
    assert r.json()["data"]["total"] == 0


def test_ledger_invalid_type(client, admin_token):
    r = client.get("/api/v1/inventory/ledger?type=bogus", headers=auth_headers(admin_token))
    assert r.status_code == 400
