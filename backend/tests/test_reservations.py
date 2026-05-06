import uuid
from datetime import datetime, timedelta

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
    r = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers(token),
        json={
            "product_id": product_id,
            "quantity_delta": qty,
            "reason": "seed for reservations",
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


def test_reserve_decreases_available(client, admin_token):
    p = _make_product(client, admin_token, "RSV-1")
    _stock_in(client, admin_token, p["product_id"], 10)

    r = client.post(
        "/api/v1/reservations",
        headers={**auth_headers(admin_token), "Idempotency-Key": str(uuid.uuid4())},
        json={"product_id": p["product_id"], "quantity": 4, "reference": "ORDER-1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert body["status"] == "active"
    assert body["quantity"] == 4
    assert body["reserve_ledger_id"] is not None

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["on_hand"] == 10
    assert snap["reserved"] == 4
    assert snap["available"] == 6


def test_reserve_insufficient_stock_returns_422(client, admin_token):
    p = _make_product(client, admin_token, "RSV-INS")
    _stock_in(client, admin_token, p["product_id"], 3)

    r = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 5},
    )
    assert r.status_code == 422


def test_release_restores_available(client, admin_token):
    p = _make_product(client, admin_token, "RSV-REL")
    _stock_in(client, admin_token, p["product_id"], 10)

    r = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 4},
    )
    rid = r.json()["data"]["reservation_id"]

    r2 = client.delete(f"/api/v1/reservations/{rid}", headers=auth_headers(admin_token))
    assert r2.status_code == 200
    body = r2.json()["data"]
    assert body["status"] == "released"
    assert body["release_ledger_id"] is not None

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["reserved"] == 0
    assert snap["available"] == 10


def test_release_already_released_rejected(client, admin_token):
    p = _make_product(client, admin_token, "RSV-DBL")
    _stock_in(client, admin_token, p["product_id"], 5)
    r = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 2},
    ).json()["data"]
    client.delete(f"/api/v1/reservations/{r['reservation_id']}", headers=auth_headers(admin_token))
    r2 = client.delete(
        f"/api/v1/reservations/{r['reservation_id']}", headers=auth_headers(admin_token)
    )
    assert r2.status_code == 422


def test_idempotency_returns_same_reservation(client, admin_token):
    p = _make_product(client, admin_token, "RSV-IDEM")
    _stock_in(client, admin_token, p["product_id"], 10)

    key = str(uuid.uuid4())
    body = {"product_id": p["product_id"], "quantity": 3, "reference": "ORDER-IDEM"}
    r1 = client.post(
        "/api/v1/reservations",
        headers={**auth_headers(admin_token), "Idempotency-Key": key},
        json=body,
    )
    assert r1.status_code == 201
    rid1 = r1.json()["data"]["reservation_id"]

    r2 = client.post(
        "/api/v1/reservations",
        headers={**auth_headers(admin_token), "Idempotency-Key": key},
        json=body,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["reservation_id"] == rid1

    snap = _snapshot(client, admin_token, p["product_id"])
    # Only one reservation applied
    assert snap["reserved"] == 3


def test_reference_idempotency_without_key(client, admin_token):
    """Same (product_id, reference) twice without idempotency key returns
    existing active reservation."""
    p = _make_product(client, admin_token, "RSV-REF")
    _stock_in(client, admin_token, p["product_id"], 10)

    body = {"product_id": p["product_id"], "quantity": 2, "reference": "ORDER-REF"}
    r1 = client.post("/api/v1/reservations", headers=auth_headers(admin_token), json=body)
    assert r1.status_code == 201
    rid1 = r1.json()["data"]["reservation_id"]

    r2 = client.post("/api/v1/reservations", headers=auth_headers(admin_token), json=body)
    assert r2.status_code == 201
    assert r2.json()["data"]["reservation_id"] == rid1

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["reserved"] == 2


def test_concurrent_reservation_one_fails(client, admin_token):
    """Two reservations totaling more than stock: first succeeds, second 422."""
    p = _make_product(client, admin_token, "RSV-CONC")
    _stock_in(client, admin_token, p["product_id"], 5)

    r1 = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 4, "reference": "A"},
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 2, "reference": "B"},
    )
    assert r2.status_code == 422


def test_reserve_remainder_after_partial_use(client, admin_token):
    p = _make_product(client, admin_token, "RSV-REM")
    _stock_in(client, admin_token, p["product_id"], 10)

    r1 = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 6, "reference": "A"},
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 4, "reference": "B"},
    )
    assert r2.status_code == 201

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["reserved"] == 10
    assert snap["available"] == 0


def test_list_reservations_filters(client, admin_token):
    p = _make_product(client, admin_token, "RSV-LST")
    _stock_in(client, admin_token, p["product_id"], 30)

    for ref in ("R1", "R2", "R3"):
        client.post(
            "/api/v1/reservations",
            headers=auth_headers(admin_token),
            json={"product_id": p["product_id"], "quantity": 1, "reference": ref},
        )

    r = client.get(
        f"/api/v1/reservations?product_id={p['product_id']}&status=active",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 3
    assert all(item["status"] == "active" for item in data["items"])


def test_expiry_job_releases_due(client, admin_token, db, admin_user):
    from app.models import Reservation
    from scripts.expire_reservations import run as run_expiry

    p = _make_product(client, admin_token, "RSV-EXP")
    _stock_in(client, admin_token, p["product_id"], 10)

    r = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 3, "reference": "EXP-1"},
    ).json()["data"]
    rid = r["reservation_id"]

    # Force expiry into the past
    res_row = db.get(Reservation, rid)
    res_row.expiry_timestamp = datetime.utcnow() - timedelta(hours=1)
    db.commit()

    result = run_expiry()
    assert rid in result["expired_ids"]

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["reserved"] == 0
    assert snap["available"] == 10

    # Status reflected
    r2 = client.get(f"/api/v1/reservations/{rid}", headers=auth_headers(admin_token))
    assert r2.json()["data"]["status"] == "expired"


def test_orphan_cleanup_detects_and_releases(client, admin_token, db, admin_user):
    from app.models import Reservation
    from scripts.orphan_reservations import run as run_orphan

    p = _make_product(client, admin_token, "RSV-ORP")
    _stock_in(client, admin_token, p["product_id"], 10)

    r = client.post(
        "/api/v1/reservations",
        headers=auth_headers(admin_token),
        json={"product_id": p["product_id"], "quantity": 2, "reference": "ORP-1"},
    ).json()["data"]
    rid = r["reservation_id"]

    # Push expiry far enough into the past that it qualifies as orphan
    res_row = db.get(Reservation, rid)
    res_row.expiry_timestamp = datetime.utcnow() - timedelta(days=10)
    db.commit()

    detected = run_orphan(auto_release=False)
    assert rid in detected["orphan_ids"]
    assert detected["released_ids"] == []

    # Still active
    r2 = client.get(f"/api/v1/reservations/{rid}", headers=auth_headers(admin_token))
    assert r2.json()["data"]["status"] == "active"

    released = run_orphan(auto_release=True)
    assert rid in released["released_ids"]

    snap = _snapshot(client, admin_token, p["product_id"])
    assert snap["reserved"] == 0
