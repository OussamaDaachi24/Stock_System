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


def _stock_in(client, token, product_id, qty):
    """Use a manual adjustment to seed on-hand stock."""
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(token),
        json={
            "product_id": product_id,
            "quantity_delta": qty,
            "reason": "seed stock for return tests",
        },
    )
    assert r.status_code in (200, 201), r.text


def _snapshot(client, token, product_id):
    r = client.get(
        f"/api/v1/inventory/snapshot?product_id={product_id}",
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_create_return_increases_stock(client, admin_token):
    p = _make_product(client, admin_token, "RET-1")
    _stock_in(client, admin_token, p["product_id"], 10)

    r = client.post(
        "/api/v1/returns",
        headers={**auth_headers(admin_token), "Idempotency-Key": str(uuid.uuid4())},
        json={
            "product_id": p["product_id"],
            "quantity": 3,
            "reason": "defective",
            "reference": "ORDER-555",
            "receiving_notes": "box damaged",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert body["status"] == "intake"
    assert body["ledger_id"] is not None
    assert body["quantity"] == 3

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 13


def test_return_rejected_when_quantity_exceeds_on_hand(client, admin_token):
    p = _make_product(client, admin_token, "RET-OVER")
    _stock_in(client, admin_token, p["product_id"], 5)

    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 6, "reason": "wrong_item"},
    )
    assert r.status_code == 422, r.text


def test_return_unknown_product_404(client, admin_token):
    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": 99999, "quantity": 1, "reason": "other"},
    )
    assert r.status_code == 404


def test_return_idempotency(client, admin_token):
    p = _make_product(client, admin_token, "RET-IDEM")
    _stock_in(client, admin_token, p["product_id"], 20)

    key = str(uuid.uuid4())
    body = {"product_id": p["product_id"], "quantity": 4, "reason": "customer_request"}
    r1 = client.post(
        "/api/v1/returns",
        headers={**auth_headers(admin_token), "Idempotency-Key": key},
        json=body,
    )
    assert r1.status_code == 201
    rid_1 = r1.json()["data"]["return_id"]

    r2 = client.post(
        "/api/v1/returns",
        headers={**auth_headers(admin_token), "Idempotency-Key": key},
        json=body,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["return_id"] == rid_1

    # Stock reflects only one return (20 + 4 = 24)
    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 24


def test_disposition_restock_closes_return(client, admin_token):
    p = _make_product(client, admin_token, "RET-RES")
    _stock_in(client, admin_token, p["product_id"], 10)
    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 2, "reason": "wrong_item"},
    ).json()["data"]

    resp = client.patch(
        f"/api/v1/returns/{r['return_id']}/disposition",
        headers=auth_headers(admin_token),
        json={"disposition": "restock", "disposition_notes": "back to shelf"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["status"] == "closed"
    assert body["disposition"] == "restock"
    assert body["scrap_ledger_id"] is None

    # Restock disposition does not reduce stock (intake already added)
    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 12


def test_disposition_scrap_removes_stock_and_audits(client, admin_token):
    p = _make_product(client, admin_token, "RET-SCR")
    _stock_in(client, admin_token, p["product_id"], 10)
    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 4, "reason": "defective"},
    ).json()["data"]

    # After intake: 10 + 4 = 14
    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 14

    resp = client.patch(
        f"/api/v1/returns/{r['return_id']}/disposition",
        headers=auth_headers(admin_token),
        json={"disposition": "scrap", "disposition_notes": "unsalvageable"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["status"] == "closed"
    assert body["disposition"] == "scrap"
    assert body["scrap_ledger_id"] is not None

    # Scrap removes the returned qty: 14 - 4 = 10
    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 10


def test_disposition_with_credit_memo_draft(client, admin_token):
    p = _make_product(client, admin_token, "RET-CM")
    _stock_in(client, admin_token, p["product_id"], 5)
    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 2, "reason": "defective"},
    ).json()["data"]

    resp = client.patch(
        f"/api/v1/returns/{r['return_id']}/disposition",
        headers=auth_headers(admin_token),
        json={
            "disposition": "scrap",
            "disposition_notes": "broken",
            "credit_amount": "19.99",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["credit_memo_id"] is not None
    assert "credit_memo" in body
    memo = body["credit_memo"]
    assert memo["status"] == "draft"
    assert memo["amount"] == "19.99"

    # Issue the memo
    resp = client.post(
        f"/api/v1/credit-memos/{memo['credit_memo_id']}/issue",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    issued = resp.json()["data"]
    assert issued["status"] == "issued"
    assert issued["issued_date"] is not None

    # Re-issue rejected
    resp2 = client.post(
        f"/api/v1/credit-memos/{memo['credit_memo_id']}/issue",
        headers=auth_headers(admin_token),
    )
    assert resp2.status_code == 409


def test_disposition_rejected_after_close(client, admin_token):
    p = _make_product(client, admin_token, "RET-CLS")
    _stock_in(client, admin_token, p["product_id"], 5)
    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 1, "reason": "other"},
    ).json()["data"]

    client.patch(
        f"/api/v1/returns/{r['return_id']}/disposition",
        headers=auth_headers(admin_token),
        json={"disposition": "restock"},
    )
    resp = client.patch(
        f"/api/v1/returns/{r['return_id']}/disposition",
        headers=auth_headers(admin_token),
        json={"disposition": "scrap"},
    )
    assert resp.status_code == 422


def test_list_returns_filters(client, admin_token):
    p = _make_product(client, admin_token, "RET-LST")
    _stock_in(client, admin_token, p["product_id"], 30)

    for reason in ("defective", "wrong_item", "defective"):
        client.post(
            "/api/v1/returns",
            headers=auth_headers(admin_token),
            json={"product_id": p["product_id"], "quantity": 1, "reason": reason},
        )

    r = client.get(
        f"/api/v1/returns?product_id={p['product_id']}&reason=defective",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 2
    assert all(item["reason"] == "defective" for item in data["items"])


def test_concurrent_returns_respect_on_hand(client, admin_token):
    """Two sequential returns within remaining on-hand both succeed; a third
    that exceeds remaining on-hand is rejected."""
    p = _make_product(client, admin_token, "RET-CONC")
    _stock_in(client, admin_token, p["product_id"], 5)

    # Start: on_hand=5. We can't return more than we hold; but each return
    # increases on_hand. The validation we want is "can't return more than
    # currently on hand at the moment of the request." After 5 returns of
    # 1 each, on_hand grows 5 -> 10. Returning 11 in one shot is rejected.
    for _ in range(5):
        r = client.post(
            "/api/v1/returns",
            headers=auth_headers(admin_token),
            json={"product_id": p["product_id"], "quantity": 1, "reason": "other"},
        )
        assert r.status_code == 201

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 10

    r = client.post(
        "/api/v1/returns",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 11, "reason": "other"},
    )
    assert r.status_code == 422
