from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import ServiceRecord
from app.schemas import DashboardStats, ServiceRecordOut
from app.tools import fetch_service_history

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/service-records", response_model=list[ServiceRecordOut])
def list_service_records(equipment_id: str | None = Query(None, max_length=20), db: Session = Depends(get_db)):
    stmt = select(ServiceRecord).order_by(desc(ServiceRecord.service_date))
    if equipment_id:
        stmt = stmt.where(ServiceRecord.equipment_id.ilike(f"%{equipment_id.strip()}%"))
    return db.scalars(stmt).all()


@router.get("/service-records/{equipment_id}", response_model=list[ServiceRecordOut])
def service_history(equipment_id: str):
    try:
        records = fetch_service_history(equipment_id)
    except ValidationError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "equipment_id must look like 'M-102'.")
    if not records:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No service records for {equipment_id.upper()}.")
    return records


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    return services.dashboard_stats(db)
