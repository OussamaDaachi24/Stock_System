import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import ExportJob, User
from ..schemas import APIResponse, ExportJobOut, InventoryExportCreate
from ..services.reports import queue_inventory_export, run_inventory_export


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("/inventory-export", response_model=APIResponse, status_code=202)
def create_inventory_export(
    payload: InventoryExportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "viewer")),
):
    job = queue_inventory_export(
        db,
        user_id=user.user_id,
        fmt=payload.format,
        category=payload.category,
        supplier_id=payload.supplier_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    # Run synchronously here (acts as in-process worker). v1 simplification.
    job = run_inventory_export(db, job)
    write_audit(
        db,
        user_id=user.user_id,
        action="create",
        entity_type="export_job",
        entity_id=None,
        new_value={"job_id": job.job_id, "format": job.format, "status": job.status},
    )
    db.commit()
    return APIResponse(data=ExportJobOut.model_validate(job).model_dump(mode="json"))


@router.get("/inventory-export/{job_id}", response_model=APIResponse)
def get_export_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=ExportJobOut.model_validate(job).model_dump(mode="json"))


@router.get("/inventory-export/{job_id}/download")
def download_export(
    job_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    job = db.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=409, detail="Export not ready")
    media = "text/csv" if job.format == "csv" else "application/json"
    filename = os.path.basename(job.file_path)
    return FileResponse(job.file_path, media_type=media, filename=filename)
