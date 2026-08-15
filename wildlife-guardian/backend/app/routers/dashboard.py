from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    total_animals = db.query(models.Animal).count()
    active_collars = db.query(models.Collar).filter(models.Collar.is_active == True).count()  # noqa: E712
    open_alerts = db.query(models.PoachingAlert).filter(
        models.PoachingAlert.status.in_(
            [models.AlertStatus.NEW, models.AlertStatus.ACKNOWLEDGED, models.AlertStatus.DISPATCHED]
        )
    ).count()
    critical_7d = db.query(models.PoachingAlert).filter(
        models.PoachingAlert.severity == models.AlertSeverity.CRITICAL,
        models.PoachingAlert.detected_at >= week_ago,
    ).count()
    patrols_week = db.query(models.Patrol).filter(models.Patrol.scheduled_date >= week_ago).count()
    snares_pending = db.query(models.SnareDetection).filter(
        models.SnareDetection.status == "pending_removal"
    ).count()
    total_raised = db.query(models.Donation).with_entities(
        models.Donation.amount_usd
    ).all()
    total_raised_sum = sum(x[0] for x in total_raised) if total_raised else 0.0
    active_campaigns = db.query(models.Campaign).filter(models.Campaign.is_active == True).count()  # noqa: E712
    community_reached = db.query(models.CommunityMember).filter(
        models.CommunityMember.opted_in == True  # noqa: E712
    ).count()

    return schemas.DashboardSummary(
        total_animals_tracked=total_animals,
        active_collars=active_collars,
        open_alerts=open_alerts,
        critical_alerts_7d=critical_7d,
        patrols_this_week=patrols_week,
        snares_pending_removal=snares_pending,
        total_raised_usd=round(total_raised_sum, 2),
        active_campaigns=active_campaigns,
        community_members_reached=community_reached,
    )
