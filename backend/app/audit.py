from typing import Any, Optional

from sqlalchemy.orm import Session

from .models import AuditLog


def write_audit(
    db: Session,
    *,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    reason: Optional[str] = None,
    request_id: Optional[str] = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        request_id=request_id,
    )
    db.add(log)
    return log


def serialize_product(product: Any) -> dict:
    return {
        "product_id": product.product_id,
        "sku": product.sku,
        "name": product.name,
        "barcode": product.barcode,
        "unit_of_measure": product.unit_of_measure,
        "category": product.category,
        "cost_price": str(product.cost_price) if product.cost_price is not None else None,
        "sell_price": str(product.sell_price) if product.sell_price is not None else None,
        "reorder_threshold": product.reorder_threshold,
        "supplier_id": product.supplier_id,
        "location": product.location,
        "attributes": product.attributes,
    }
