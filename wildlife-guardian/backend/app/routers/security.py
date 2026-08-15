from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["security"])


@router.get("/sensors", response_model=List[schemas.SensorNodeOut])
def list_sensors(online_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(models.SensorNode)
    if online_only:
        q = q.filter(models.SensorNode.is_online == True)  # noqa: E712
    return q.all()


@router.get("/alerts", response_model=List[schemas.PoachingAlertOut])
def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    q = db.query(models.PoachingAlert).filter(models.PoachingAlert.detected_at >= since)
    if status:
        try:
            q = q.filter(models.PoachingAlert.status == models.AlertStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
    if severity:
        try:
            q = q.filter(models.PoachingAlert.severity == models.AlertSeverity(severity))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity '{severity}'")
    return q.order_by(models.PoachingAlert.detected_at.desc()).all()


@router.post("/alerts", response_model=schemas.PoachingAlertOut, status_code=201)
def create_alert(payload: schemas.PoachingAlertCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    try:
        data["severity"] = models.AlertSeverity(data["severity"])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity value")
    alert = models.PoachingAlert(**data)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/alerts/{alert_id}/status", response_model=schemas.PoachingAlertOut)
def update_alert_status(alert_id: str, payload: schemas.AlertStatusUpdate, db: Session = Depends(get_db)):
    alert = db.query(models.PoachingAlert).filter(models.PoachingAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    try:
        new_status = models.AlertStatus(payload.status)
    except ValueError:
        valid = [s.value for s in models.AlertStatus]
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    alert.status = new_status
    if new_status == models.AlertStatus.RESOLVED:
        alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/drone-missions", response_model=List[schemas.DroneMissionOut])
def list_drone_missions(db: Session = Depends(get_db)):
    return db.query(models.DroneMission).order_by(models.DroneMission.launched_at.desc()).all()


@router.get("/snares", response_model=List[schemas.SnareDetectionOut])
def list_snares(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.SnareDetection)
    if status:
        q = q.filter(models.SnareDetection.status == status)
    return q.order_by(models.SnareDetection.detected_at.desc()).all()


@router.patch("/snares/{snare_id}/clear", response_model=schemas.SnareDetectionOut)
def clear_snare(snare_id: str, ranger_id: Optional[str] = None, db: Session = Depends(get_db)):
    snare = db.query(models.SnareDetection).filter(models.SnareDetection.id == snare_id).first()
    if not snare:
        raise HTTPException(status_code=404, detail="Snare detection not found")
    snare.status = "removed"
    snare.cleared_at = datetime.utcnow()
    snare.cleared_by_ranger_id = ranger_id
    db.commit()
    db.refresh(snare)
    return snare
