import csv
import io
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..models import ExportJob, Product, StockSnapshot


_EXPORT_DIR = os.path.join(tempfile.gettempdir(), "stock_system_exports")
os.makedirs(_EXPORT_DIR, exist_ok=True)


def export_dir() -> str:
    return _EXPORT_DIR


def new_job_id() -> str:
    return uuid.uuid4().hex


def queue_inventory_export(
    db: Session,
    user_id: int,
    fmt: str,
    category: Optional[str],
    supplier_id: Optional[int],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
) -> ExportJob:
    job = ExportJob(
        job_id=new_job_id(),
        user_id=user_id,
        format=fmt,
        filters={
            "category": category,
            "supplier_id": supplier_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_inventory_export(db: Session, job: ExportJob) -> ExportJob:
    """Execute the export synchronously (acts as our 'background worker')."""
    job.status = "in_progress"
    db.commit()

    try:
        filters = job.filters or {}
        q = db.query(Product, StockSnapshot).outerjoin(
            StockSnapshot, StockSnapshot.product_id == Product.product_id
        )
        if filters.get("category"):
            q = q.filter(Product.category == filters["category"])
        if filters.get("supplier_id") is not None:
            q = q.filter(Product.supplier_id == filters["supplier_id"])
        rows = q.all()

        ext = "csv" if job.format == "csv" else "json"
        path = os.path.join(_EXPORT_DIR, f"inventory_{job.job_id}.{ext}")

        if job.format == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                ["product_id", "sku", "name", "category", "supplier_id",
                 "on_hand", "reserved", "available", "reorder_threshold"]
            )
            for product, snap in rows:
                writer.writerow([
                    product.product_id,
                    product.sku,
                    product.name,
                    product.category or "",
                    product.supplier_id or "",
                    snap.on_hand if snap else 0,
                    snap.reserved if snap else 0,
                    snap.available if snap else 0,
                    product.reorder_threshold or "",
                ])
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(buf.getvalue())
        else:
            payload = []
            for product, snap in rows:
                payload.append({
                    "product_id": product.product_id,
                    "sku": product.sku,
                    "name": product.name,
                    "category": product.category,
                    "supplier_id": product.supplier_id,
                    "on_hand": snap.on_hand if snap else 0,
                    "reserved": snap.reserved if snap else 0,
                    "available": snap.available if snap else 0,
                    "reorder_threshold": product.reorder_threshold,
                })
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)

        job.file_path = path
        job.download_url = f"/api/v1/reports/inventory-export/{job.job_id}/download"
        job.expires_at = datetime.utcnow() + timedelta(hours=1)
        job.status = "completed"
        job.completed_at = datetime.utcnow()
    except Exception as e:  # noqa: BLE001
        job.status = "failed"
        job.error = str(e)[:1000]
        job.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job
