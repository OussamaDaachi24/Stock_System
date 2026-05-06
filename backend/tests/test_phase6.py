from tests.conftest import auth_headers


def _create_product(client, token, sku="SKU-PH6", qty=0):
    r = client.post(
        "/api/v1/products",
        json={"sku": sku, "name": "P6 Item", "unit_of_measure": "piece",
              "category": "general", "reorder_threshold": 5},
        headers=auth_headers(token),
    )
    assert r.status_code in (200, 201), r.text
    pid = r.json()["data"]["product_id"]
    if qty > 0:
        r = client.post(
            "/api/v1/inventory/adjustments",
            json={"product_id": pid, "quantity_delta": qty, "reason": "seed"},
            headers=auth_headers(token),
        )
        assert r.status_code in (200, 201), r.text
    return pid


def test_health_full(client):
    r = client.get("/api/v1/health/full")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["service"] == "stock-system"
    assert data["db"] == "ok"


def test_metrics_requires_auth(client, manager_token, admin_token):
    r = client.get("/api/v1/metrics")
    assert r.status_code == 401
    r = client.get("/api/v1/metrics", headers=auth_headers(manager_token))
    assert r.status_code == 200
    data = r.json()["data"]
    assert "products" in data and "ledger_entries" in data


def test_inventory_export_csv(client, admin_token):
    pid = _create_product(client, admin_token, qty=10)
    r = client.post(
        "/api/v1/reports/inventory-export",
        json={"format": "csv"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 202, r.text
    job = r.json()["data"]
    assert job["status"] == "completed"
    assert job["download_url"]

    # Poll
    r2 = client.get(f"/api/v1/reports/inventory-export/{job['job_id']}",
                    headers=auth_headers(admin_token))
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "completed"

    # Download
    r3 = client.get(f"/api/v1/reports/inventory-export/{job['job_id']}/download",
                    headers=auth_headers(admin_token))
    assert r3.status_code == 200
    body = r3.content.decode()
    assert "sku" in body and "SKU-PH6" in body


def test_inventory_export_json(client, admin_token):
    _create_product(client, admin_token, sku="J-1", qty=2)
    r = client.post(
        "/api/v1/reports/inventory-export",
        json={"format": "json"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 202
    job = r.json()["data"]
    r3 = client.get(f"/api/v1/reports/inventory-export/{job['job_id']}/download",
                    headers=auth_headers(admin_token))
    assert r3.status_code == 200
    rows = r3.json()
    assert any(row["sku"] == "J-1" for row in rows)


def test_backup_and_restore(client, admin_token):
    pid = _create_product(client, admin_token, sku="BK-1", qty=7)

    r = client.post("/api/v1/admin/backups", headers=auth_headers(admin_token))
    assert r.status_code == 202, r.text
    backup = r.json()["data"]
    assert backup["status"] == "completed"
    bid = backup["backup_id"]

    rl = client.get("/api/v1/admin/backups", headers=auth_headers(admin_token))
    assert rl.status_code == 200
    assert any(b["backup_id"] == bid for b in rl.json()["data"])

    # Mutate after backup
    r = client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": pid, "quantity_delta": 100, "reason": "post-backup"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code in (200, 201)
    snap = client.get(f"/api/v1/inventory/snapshot?product_id={pid}",
                      headers=auth_headers(admin_token)).json()["data"]
    assert snap["on_hand"] == 107

    # Restore
    rr = client.post(
        "/api/v1/admin/restore",
        json={"backup_id": bid, "verify": True},
        headers=auth_headers(admin_token),
    )
    assert rr.status_code == 200, rr.text
    assert rr.json()["data"]["restored_tables"]["products"] >= 1


def test_backup_admin_only(client, manager_token):
    r = client.post("/api/v1/admin/backups", headers=auth_headers(manager_token))
    assert r.status_code == 403
