import uuid

from tests.conftest import auth_headers


def _make_product(client, token, sku, **extra):
    payload = {
        "sku": sku,
        "name": f"Product {sku}",
        "unit_of_measure": "piece",
        **extra,
    }
    r = client.post("/api/v1/products", headers=auth_headers(token), json=payload)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def _make_supplier(client, token, name="Acme Co"):
    r = client.post(
        "/api/v1/suppliers",
        headers=auth_headers(token),
        json={"name": name, "contact_email": "vendor@example.com"},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


def _make_po(client, token, supplier_id, products, po_number="PO-1"):
    lines = [{"product_id": p["product_id"], "quantity": qty, "unit_price": "10.00"} for p, qty in products]
    r = client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers(token),
        json={"supplier_id": supplier_id, "po_number": po_number, "lines": lines},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


# --- Suppliers ---
def test_create_and_list_supplier(client, admin_token):
    s = _make_supplier(client, admin_token, name="Globex")
    assert s["supplier_id"] > 0
    assert s["name"] == "Globex"

    r = client.get("/api/v1/suppliers", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1


# --- Purchase Orders ---
def test_create_po_and_unique_number(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "PO-A")

    po = _make_po(client, admin_token, s["supplier_id"], [(p, 50)], po_number="PO-100")
    assert po["status"] == "open"
    assert len(po["lines"]) == 1
    assert po["lines"][0]["received_quantity"] == 0

    # Duplicate number rejected
    r = client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers(admin_token),
        json={
            "supplier_id": s["supplier_id"],
            "po_number": "PO-100",
            "lines": [{"product_id": p["product_id"], "quantity": 1}],
        },
    )
    assert r.status_code == 409


def test_po_unknown_supplier_404(client, admin_token):
    p = _make_product(client, admin_token, "PO-MS")
    r = client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers(admin_token),
        json={
            "supplier_id": 9999,
            "po_number": "PO-X",
            "lines": [{"product_id": p["product_id"], "quantity": 1}],
        },
    )
    assert r.status_code == 404


# --- Receiving full happy path ---
def test_full_receive_completes_po_and_updates_stock(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-1")
    po = _make_po(client, admin_token, s["supplier_id"], [(p, 50)], po_number="PO-200")

    r = client.post(
        "/api/v1/receipts",
        headers={**auth_headers(admin_token), "Idempotency-Key": str(uuid.uuid4())},
        json={
            "po_id": po["po_id"],
            "lines": [{"product_id": p["product_id"], "quantity": 50, "location": "A1"}],
        },
    )
    assert r.status_code == 201, r.text
    receipt = r.json()["data"]
    assert receipt["status"] == "partial"
    assert not receipt.get("discrepancies")
    receipt_id = receipt["receipt_id"]

    # Stock updated
    r = client.get(
        f"/api/v1/inventory/snapshot?product_id={p['product_id']}",
        headers=auth_headers(admin_token),
    )
    assert r.json()["data"]["on_hand"] == 50

    # Complete receipt
    r = client.post(
        f"/api/v1/receipts/{receipt_id}/complete",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    completed = r.json()["data"]
    assert completed["status"] == "completed"
    assert len(completed["put_away_tasks"]) == 1

    # PO closed
    r = client.get(f"/api/v1/purchase-orders/{po['po_id']}", headers=auth_headers(admin_token))
    assert r.json()["data"]["status"] == "closed"


def test_partial_receive_then_complete(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-PART")
    po = _make_po(client, admin_token, s["supplier_id"], [(p, 100)], po_number="PO-300")

    # First partial
    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={"po_id": po["po_id"], "lines": [{"product_id": p["product_id"], "quantity": 40}]},
    )
    assert r.status_code == 201

    r = client.get(f"/api/v1/purchase-orders/{po['po_id']}", headers=auth_headers(admin_token))
    assert r.json()["data"]["status"] == "partial"

    # Second partial completes the PO line
    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={"po_id": po["po_id"], "lines": [{"product_id": p["product_id"], "quantity": 60}]},
    )
    assert r.status_code == 201

    r = client.get(f"/api/v1/purchase-orders/{po['po_id']}", headers=auth_headers(admin_token))
    assert r.json()["data"]["status"] == "closed"


def test_over_receipt_flags_discrepancy(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-OVER")
    po = _make_po(client, admin_token, s["supplier_id"], [(p, 50)], po_number="PO-400")

    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={"po_id": po["po_id"], "lines": [{"product_id": p["product_id"], "quantity": 60}]},
    )
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert body["discrepancies"]
    over = [d for d in body["discrepancies"] if d["type"] == "over"]
    assert over and over[0]["received"] == 60 and over[0]["expected"] == 50

    # Stock still reflects actual physical receipt (60)
    r = client.get(
        f"/api/v1/inventory/snapshot?product_id={p['product_id']}",
        headers=auth_headers(admin_token),
    )
    assert r.json()["data"]["on_hand"] == 60


def test_unknown_item_flagged(client, admin_token):
    s = _make_supplier(client, admin_token)
    p_on_po = _make_product(client, admin_token, "RCV-PO")
    p_unknown = _make_product(client, admin_token, "RCV-UNK")
    po = _make_po(client, admin_token, s["supplier_id"], [(p_on_po, 10)], po_number="PO-500")

    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={
            "po_id": po["po_id"],
            "lines": [
                {"product_id": p_on_po["product_id"], "quantity": 10},
                {"product_id": p_unknown["product_id"], "quantity": 5},
            ],
        },
    )
    assert r.status_code == 201
    discs = r.json()["data"]["discrepancies"]
    assert any(d["type"] == "unknown" and d["product_id"] == p_unknown["product_id"] for d in discs)


def test_under_receipt_detected_on_complete(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-UND")
    po = _make_po(client, admin_token, s["supplier_id"], [(p, 100)], po_number="PO-600")

    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={"po_id": po["po_id"], "lines": [{"product_id": p["product_id"], "quantity": 70}]},
    )
    receipt_id = r.json()["data"]["receipt_id"]

    r = client.post(f"/api/v1/receipts/{receipt_id}/complete", headers=auth_headers(admin_token))
    assert r.status_code == 200
    discs = r.json()["data"]["discrepancies"] or []
    under = [d for d in discs if d["type"] == "under"]
    assert under and under[0]["expected"] == 100 and under[0]["received"] == 70

    # PO should still be partial (not closed) since it's not fully received
    r = client.get(f"/api/v1/purchase-orders/{po['po_id']}", headers=auth_headers(admin_token))
    assert r.json()["data"]["status"] == "partial"


def test_receipt_without_po(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-NOPO")

    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={
            "supplier_id": s["supplier_id"],
            "lines": [{"product_id": p["product_id"], "quantity": 25}],
        },
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["po_id"] is None
    # No PO → no discrepancy from PO matching
    assert not body.get("discrepancies")


def test_receipt_idempotency(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-IDEM")
    po = _make_po(client, admin_token, s["supplier_id"], [(p, 30)], po_number="PO-700")

    key = str(uuid.uuid4())
    body = {"po_id": po["po_id"], "lines": [{"product_id": p["product_id"], "quantity": 30}]}

    r1 = client.post(
        "/api/v1/receipts",
        headers={**auth_headers(admin_token), "Idempotency-Key": key},
        json=body,
    )
    assert r1.status_code == 201
    rid_1 = r1.json()["data"]["receipt_id"]

    r2 = client.post(
        "/api/v1/receipts",
        headers={**auth_headers(admin_token), "Idempotency-Key": key},
        json=body,
    )
    assert r2.status_code == 200  # cached
    rid_2 = r2.json()["data"]["receipt_id"]
    assert rid_1 == rid_2

    # Stock reflects only one receipt
    r = client.get(
        f"/api/v1/inventory/snapshot?product_id={p['product_id']}",
        headers=auth_headers(admin_token),
    )
    assert r.json()["data"]["on_hand"] == 30


def test_cannot_receive_against_closed_po(client, admin_token):
    s = _make_supplier(client, admin_token)
    p = _make_product(client, admin_token, "RCV-CLS")
    po = _make_po(client, admin_token, s["supplier_id"], [(p, 5)], po_number="PO-800")

    # Cancel PO
    r = client.post(
        f"/api/v1/purchase-orders/{po['po_id']}/cancel", headers=auth_headers(admin_token)
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={"po_id": po["po_id"], "lines": [{"product_id": p["product_id"], "quantity": 1}]},
    )
    assert r.status_code == 409


def test_complete_receipt_generates_put_away_tasks(client, admin_token):
    s = _make_supplier(client, admin_token)
    p1 = _make_product(client, admin_token, "RCV-T1")
    p2 = _make_product(client, admin_token, "RCV-T2")
    po = _make_po(client, admin_token, s["supplier_id"], [(p1, 5), (p2, 7)], po_number="PO-900")

    r = client.post(
        "/api/v1/receipts",
        headers=auth_headers(admin_token),
        json={
            "po_id": po["po_id"],
            "lines": [
                {"product_id": p1["product_id"], "quantity": 5, "location": "Bin-A"},
                {"product_id": p2["product_id"], "quantity": 7, "location": "Bin-B"},
            ],
        },
    )
    receipt_id = r.json()["data"]["receipt_id"]

    r = client.post(f"/api/v1/receipts/{receipt_id}/complete", headers=auth_headers(admin_token))
    tasks = r.json()["data"]["put_away_tasks"]
    assert len(tasks) == 2
    assert {t["to_location"] for t in tasks} == {"Bin-A", "Bin-B"}

    r = client.get(
        f"/api/v1/receipts/{receipt_id}/put-away-tasks", headers=auth_headers(admin_token)
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2
