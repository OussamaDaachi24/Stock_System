"""Phase 2 live integration: ledger, snapshot, adjustments, reconciliation, low-stock.

Usage:
    python -m scripts.integration_test_phase2 [--base http://localhost:8000]
"""
import argparse
import sys
import time
import uuid

import httpx


def step(msg: str) -> None:
    print(f"  -> {msg}")


def assert_eq(actual, expected, label: str) -> None:
    if actual != expected:
        print(f"FAIL [{label}]: expected {expected!r}, got {actual!r}")
        sys.exit(1)
    step(f"OK  [{label}] = {actual!r}")


def assert_true(cond: bool, label: str) -> None:
    if not cond:
        print(f"FAIL [{label}]")
        sys.exit(1)
    step(f"OK  [{label}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--admin-email", default="admin@example.com")
    ap.add_argument("--admin-password", default="ChangeMe123!")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    print(f"\n=== Phase 2 integration test against {base} ===\n")

    deadline = time.time() + 20
    while True:
        try:
            r = httpx.get(f"{base}/api/v1/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        if time.time() > deadline:
            print("FAIL: server unreachable"); sys.exit(1)
        time.sleep(0.5)

    print("[1] login")
    r = httpx.post(f"{base}/api/v1/auth/login", json={"email": args.admin_email, "password": args.admin_password})
    assert_eq(r.status_code, 200, "login")
    headers = {"Authorization": f"Bearer {r.json()['data']['tokens']['access_token']}"}

    print("\n[2] create product with reorder threshold")
    sku = f"P2-{uuid.uuid4().hex[:8]}"
    r = httpx.post(
        f"{base}/api/v1/products",
        headers=headers,
        json={"sku": sku, "name": "Inventory Test", "unit_of_measure": "piece", "reorder_threshold": 10},
    )
    assert_eq(r.status_code, 201, "create_product")
    pid = r.json()["data"]["product_id"]

    print("\n[3] empty snapshot for new product")
    r = httpx.get(f"{base}/api/v1/inventory/snapshot?product_id={pid}", headers=headers)
    assert_eq(r.status_code, 200, "snapshot.fresh.status")
    assert_eq(r.json()["data"]["on_hand"], 0, "snapshot.fresh.on_hand")

    print("\n[4] adjustment +50 -> snapshot updates")
    r = httpx.post(
        f"{base}/api/v1/inventory/adjustments",
        headers=headers,
        json={"product_id": pid, "quantity_delta": 50, "reason": "Receiving init", "allow_negative": True},
    )
    assert_eq(r.status_code, 201, "adj.create")
    ledger_id = r.json()["data"]["ledger_id"]
    assert_eq(r.json()["data"]["on_hand"], 50, "adj.on_hand")

    r = httpx.get(f"{base}/api/v1/inventory/snapshot?product_id={pid}", headers=headers)
    assert_eq(r.json()["data"]["on_hand"], 50, "snapshot.after_adj.on_hand")

    print("\n[5] ledger has the entry")
    r = httpx.get(f"{base}/api/v1/inventory/ledger?product_id={pid}", headers=headers)
    assert_eq(r.status_code, 200, "ledger.list")
    items = r.json()["data"]["items"]
    assert_eq(len(items), 1, "ledger.count")
    assert_eq(items[0]["type"], "adjustment", "ledger.type")
    assert_eq(items[0]["quantity_delta"], 50, "ledger.delta")

    print("\n[6] negative-stock blocked by default (422 + code)")
    r = httpx.post(
        f"{base}/api/v1/inventory/adjustments",
        headers=headers,
        json={"product_id": pid, "quantity_delta": -200, "reason": "should fail"},
    )
    assert_eq(r.status_code, 422, "neg.status")
    detail = r.json()["error"]["message"]
    assert_eq(detail.get("code"), "NEGATIVE_STOCK_NOT_ALLOWED", "neg.code")

    print("\n[7] ledger filter by type")
    r = httpx.get(f"{base}/api/v1/inventory/ledger?product_id={pid}&type=adjustment", headers=headers)
    assert_eq(r.json()["data"]["total"], 1, "ledger.adjustment_count")
    r = httpx.get(f"{base}/api/v1/inventory/ledger?product_id={pid}&type=receiving", headers=headers)
    assert_eq(r.json()["data"]["total"], 0, "ledger.receiving_count")

    print("\n[8] adjustment idempotency replay")
    key = str(uuid.uuid4())
    body = {"product_id": pid, "quantity_delta": 5, "reason": "Idem test", "allow_negative": True}
    r1 = httpx.post(f"{base}/api/v1/inventory/adjustments", headers={**headers, "Idempotency-Key": key}, json=body)
    r2 = httpx.post(f"{base}/api/v1/inventory/adjustments", headers={**headers, "Idempotency-Key": key}, json=body)
    assert_eq(r1.status_code, 201, "idem.first")
    assert_eq(r2.status_code, 200, "idem.replay")
    assert_eq(r1.json()["data"]["ledger_id"], r2.json()["data"]["ledger_id"], "idem.same_ledger_id")

    print("\n[9] reconciliation: detects no drift after clean ops")
    r = httpx.post(f"{base}/api/v1/inventory/reconcile", headers=headers)
    assert_eq(r.status_code, 200, "reconcile.status")
    assert_eq(r.json()["data"]["mismatches_found"], 0, "reconcile.no_drift")

    print("\n[10] low-stock: product with 55 on_hand, threshold 10 -> not flagged")
    r = httpx.get(f"{base}/api/v1/inventory/low-stock", headers=headers)
    assert_eq(r.status_code, 200, "low_stock.status")
    flagged_skus = {row["sku"] for row in r.json()["data"]}
    assert_true(sku not in flagged_skus, "low_stock.not_flagged_when_above")

    print("\n[11] drain stock to below threshold; low-stock flags it")
    httpx.post(
        f"{base}/api/v1/inventory/adjustments",
        headers=headers,
        json={"product_id": pid, "quantity_delta": -50, "reason": "deplete", "allow_negative": True},
    )
    r = httpx.get(f"{base}/api/v1/inventory/low-stock", headers=headers)
    flagged_skus = {row["sku"] for row in r.json()["data"]}
    assert_true(sku in flagged_skus, "low_stock.flagged_when_below")

    print("\n[12] unauthenticated ledger query -> 401")
    r = httpx.get(f"{base}/api/v1/inventory/ledger")
    assert_eq(r.status_code, 401, "unauth.status")

    print("\n=== ALL PHASE 2 INTEGRATION CHECKS PASSED ===\n")


if __name__ == "__main__":
    main()
