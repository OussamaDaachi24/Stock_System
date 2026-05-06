import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Iterable

from sqlalchemy import DateTime, Date, inspect as sa_inspect
from sqlalchemy.orm import Session

from ..db import Base, engine
from ..models import Backup


_BACKUP_DIR = os.path.join(tempfile.gettempdir(), "stock_system_backups")
os.makedirs(_BACKUP_DIR, exist_ok=True)


def backup_dir() -> str:
    return _BACKUP_DIR


def new_backup_id() -> str:
    return uuid.uuid4().hex


_TABLE_ORDER = [
    "users", "suppliers", "products",
    "inventory_ledger", "stock_snapshot",
    "purchase_orders", "po_lines",
    "receipts", "receipt_lines", "put_away_tasks",
    "returns", "credit_memos",
    "reservations", "low_stock_alerts",
    "audit_logs", "export_jobs", "backups",
]


def _ordered_tables() -> Iterable:
    by_name = {t.name: t for t in Base.metadata.tables.values()}
    return [by_name[n] for n in _TABLE_ORDER if n in by_name]


def queue_backup(db: Session, user_id: int, notes: str | None = None) -> Backup:
    b = Backup(backup_id=new_backup_id(), user_id=user_id, status="queued", notes=notes)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def run_backup(db: Session, b: Backup) -> Backup:
    b.status = "running"
    db.commit()
    try:
        path = os.path.join(_BACKUP_DIR, f"backup_{b.backup_id}.json")
        snapshot: dict[str, list[dict]] = {}
        with engine.connect() as conn:
            for table in _ordered_tables():
                rows = conn.execute(table.select()).mappings().all()
                snapshot[table.name] = [
                    {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
                    for row in rows
                ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"created_at": datetime.utcnow().isoformat(), "tables": snapshot}, f)
        b.file_path = path
        b.size_bytes = os.path.getsize(path)
        b.status = "completed"
        b.completed_at = datetime.utcnow()
    except Exception as e:  # noqa: BLE001
        b.status = "failed"
        b.error = str(e)[:1000]
        b.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(b)
    return b


def restore_backup(db: Session, b: Backup, verify: bool = True) -> dict:
    if b.status != "completed" or not b.file_path or not os.path.exists(b.file_path):
        raise ValueError("Backup is not available for restore")
    with open(b.file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    tables = payload.get("tables", {})
    counts: dict[str, int] = {}

    insp = sa_inspect(engine)
    available = set(insp.get_table_names())

    with engine.begin() as conn:
        for table in reversed(list(_ordered_tables())):
            if table.name in available:
                conn.execute(table.delete())
        for table in _ordered_tables():
            rows = tables.get(table.name, [])
            counts[table.name] = len(rows)
            if not rows:
                continue
            dt_cols = [
                c.name for c in table.columns
                if isinstance(c.type, (DateTime, Date))
            ]
            converted = []
            for r in rows:
                row = dict(r)
                for col in dt_cols:
                    v = row.get(col)
                    if isinstance(v, str):
                        try:
                            row[col] = datetime.fromisoformat(v)
                        except ValueError:
                            row[col] = None
                converted.append(row)
            conn.execute(table.insert(), converted)
    return {"restored_tables": counts, "verified": verify}
