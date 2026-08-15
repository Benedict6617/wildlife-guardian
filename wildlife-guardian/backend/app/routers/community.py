from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.sms_gateway import get_gateway

router = APIRouter(prefix="/api/v1", tags=["community"])


@router.get("/community-members", response_model=List[schemas.CommunityMemberOut])
def list_members(zone_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.CommunityMember).filter(models.CommunityMember.opted_in == True)  # noqa: E712
    if zone_id:
        q = q.filter(models.CommunityMember.zone_id == zone_id)
    return q.all()


@router.get("/sms-alerts", response_model=List[schemas.SMSAlertOut])
def list_sms_alerts(db: Session = Depends(get_db)):
    return db.query(models.SMSAlert).order_by(models.SMSAlert.sent_at.desc()).all()


@router.post("/sms-alerts/broadcast", response_model=schemas.SMSAlertOut, status_code=201)
def broadcast_sms(payload: schemas.SMSBroadcastRequest, db: Session = Depends(get_db)):
    q = db.query(models.CommunityMember).filter(models.CommunityMember.opted_in == True)  # noqa: E712
    if payload.zone_id:
        q = q.filter(models.CommunityMember.zone_id == payload.zone_id)
    recipients = [m.phone_number for m in q.all()]

    if not recipients:
        raise HTTPException(status_code=422, detail="No opted-in recipients found for this zone")

    gateway = get_gateway()
    result = gateway.send(recipients, payload.message)

    record = models.SMSAlert(
        category=payload.category,
        message=payload.message,
        recipient_count=result["delivered"],
        zone_id=payload.zone_id,
        related_alert_id=payload.related_alert_id,
        delivery_status=result["status"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
