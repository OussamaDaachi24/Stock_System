"""Live integration test: hits a running API over HTTP and walks the Phase 1 user flow.

Usage:
    python -m scripts.integration_test [--base http://localhost:8000]

Exits non-zero on any check failure.
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
    print(f"\n=== Phase 1 integration test against {base} ===\n")

    # Wait for server
    print("[0] health check")
    deadline = time.time() + 20
    while True:
        try:
            r = httpx.get(f"{base}/api/v1/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        if time.time() > deadline:
            print("FAIL: server did not become healthy in 20s")
            sys.exit(1)
        time.sleep(0.5)
    assert_eq(r.json()["status"], "success", "health.status")

    # Login
    print("\n[1] admin login")
    r = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"email": args.admin_email, "password": args.admin_password},
        timeout=10,
    )
    assert_eq(r.status_code, 200, "login.status_code")
    body = r.json()
    assert_eq(body["status"], "success", "login.body.status")
    access = body["data"]["tokens"]["access_token"]
    assert_true(bool(access), "login.access_token present")
    headers = {"Authorization": f"Bearer {access}"}

    # Me
    print("\n[2] /auth/me")
    r = httpx.get(f"{base}/api/v1/auth/me", headers=headers)
    assert_eq(r.status_code, 200, "me.status_code")
    assert_eq(r.json()["data"]["role"], "admin", "me.role")

    # Wrong-password login
    print("\n[3] reject wrong password")
    r = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"email": args.admin_email, "password": "wrong"},
    )
    assert_eq(r.status_code, 401, "wrong_password.status_code")

    # Create operator user (RBAC sanity)
    print("\n[4] admin creates operator user")
    op_email = f"op-{uuid.uuid4().hex[:8]}@test.com"
    r = httpx.post(
        f"{base}/api/v1/admin/users",
        headers=headers,
        json={"email": op_email, "name": "Op", "password": "Password123!", "role": "operator"},
    )
    assert_eq(r.status_code, 201, "create_user.status_code")

    # Operator login + RBAC denial
    print("\n[5] operator login + RBAC: cannot create products")
    r = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"email": op_email, "password": "Password123!"},
    )
    assert_eq(r.status_code, 200, "op_login.status_code")
    op_access = r.json()["data"]["tokens"]["access_token"]
    op_headers = {"Authorization": f"Bearer {op_access}"}

    r = httpx.post(
        f"{base}/api/v1/products",
        headers=op_headers,
        json={"sku": "X-1", "name": "X", "unit_of_measure": "piece"},
    )
    assert_eq(r.status_code, 403, "rbac.operator_create_blocked")

    # Create product (admin)
    print("\n[6] admin creates product")
    sku = f"INT-{uuid.uuid4().hex[:8]}"
    barcode = uuid.uuid4().hex[:12]
    payload = {
        "sku": sku,
        "name": "Integration Widget",
        "barcode": barcode,
        "unit_of_measure": "piece",
        "category": "integration",
        "cost_price": "1.50",
        "sell_price": "3.00",
        "reorder_threshold": 5,
    }
    r = httpx.post(f"{base}/api/v1/products", headers=headers, json=payload)
    assert_eq(r.status_code, 201, "create_product.status_code")
    pid = r.json()["data"]["product_id"]
    assert_true(isinstance(pid, int) and pid > 0, "create_product.product_id")

    # Duplicate SKU rejected
    print("\n[7] duplicate SKU rejected (409)")
    r = httpx.post(
        f"{base}/api/v1/products",
        headers=headers,
        json={**payload, "barcode": uuid.uuid4().hex[:12]},
    )
    assert_eq(r.status_code, 409, "duplicate_sku.status_code")

    # Duplicate barcode rejected
    print("\n[8] duplicate barcode rejected (409)")
    r = httpx.post(
        f"{base}/api/v1/products",
        headers=headers,
        json={**payload, "sku": f"INT-{uuid.uuid4().hex[:8]}"},
    )
    assert_eq(r.status_code, 409, "duplicate_barcode.status_code")

    # Invalid UoM
    print("\n[9] invalid UoM rejected (400)")
    r = httpx.post(
        f"{base}/api/v1/products",
        headers=headers,
        json={"sku": f"INT-{uuid.uuid4().hex[:8]}", "name": "X", "unit_of_measure": "parsec"},
    )
    assert_eq(r.status_code, 400, "invalid_uom.status_code")

    # Idempotency: same key returns same product, 200
    print("\n[10] idempotency: same key returns cached")
    key = str(uuid.uuid4())
    idem_payload = {
        "sku": f"IDEM-{uuid.uuid4().hex[:8]}",
        "name": "Idempotent",
        "unit_of_measure": "piece",
    }
    r1 = httpx.post(
        f"{base}/api/v1/products",
        headers={**headers, "Idempotency-Key": key},
        json=idem_payload,
        timeout=15,
    )
    r2 = httpx.post(
        f"{base}/api/v1/products",
        headers={**headers, "Idempotency-Key": key},
        json=idem_payload,
        timeout=15,
    )
    assert_eq(r1.status_code, 201, "idem.first.status_code")
    assert_eq(r2.status_code, 200, "idem.replay.status_code")
    assert_eq(
        r1.json()["data"]["product_id"],
        r2.json()["data"]["product_id"],
        "idem.same_product_id",
    )

    # Search
    print("\n[11] search by sku")
    r = httpx.get(f"{base}/api/v1/products", headers=headers, params={"search": sku})
    assert_eq(r.status_code, 200, "search.status_code")
    items = r.json()["data"]["items"]
    assert_true(any(i["sku"] == sku for i in items), "search.found")

    # Update
    print("\n[12] update product")
    r = httpx.put(
        f"{base}/api/v1/products/{pid}",
        headers=headers,
        json={"name": "Integration Widget v2", "category": "integration-v2"},
    )
    assert_eq(r.status_code, 200, "update.status_code")
    assert_eq(r.json()["data"]["name"], "Integration Widget v2", "update.name")

    # Update non-existent
    print("\n[13] update missing -> 404")
    r = httpx.put(
        f"{base}/api/v1/products/999999",
        headers=headers,
        json={"name": "x"},
    )
    assert_eq(r.status_code, 404, "update_missing.status_code")

    # Unauthenticated request -> 401
    print("\n[14] unauthenticated -> 401")
    r = httpx.get(f"{base}/api/v1/products")
    assert_eq(r.status_code, 401, "unauth.status_code")

    print("\n=== ALL INTEGRATION CHECKS PASSED ===\n")


if __name__ == "__main__":
    main()
