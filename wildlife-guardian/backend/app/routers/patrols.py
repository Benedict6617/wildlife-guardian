from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import patrol_optimizer

router = APIRouter(prefix="/api/v1", tags=["patrols"])


@router.get("/rangers", response_model=List[schemas.RangerOut])
def list_rangers(active_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(models.Ranger)
    if active_only:
        q = q.filter(models.Ranger.is_active_duty == True)  # noqa: E712
    return q.all()


@router.get("/patrols", response_model=List[schemas.PatrolOut])
def list_patrols(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Patrol)
    if status:
        try:
            q = q.filter(models.Patrol.status == models.PatrolStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
    return q.order_by(models.Patrol.scheduled_date.desc()).all()


@router.get("/patrols/{patrol_id}", response_model=schemas.PatrolOut)
def get_patrol(patrol_id: str, db: Session = Depends(get_db)):
    patrol = db.query(models.Patrol).filter(models.Patrol.id == patrol_id).first()
    if not patrol:
        raise HTTPException(status_code=404, detail="Patrol not found")
    return patrol


@router.post("/patrols/generate", response_model=schemas.PatrolOut, status_code=201)
def generate_patrol(payload: schemas.PatrolGenerateRequest, db: Session = Depends(get_db)):
    """
    Optimizer-driven patrol creation: pulls active alerts, sensor health,
    and pending snare removals inside the zone into a prioritized,
    distance-ordered route. See services/patrol_optimizer.py for the method.
    """
    zone = db.query(models.HabitatZone).filter(models.HabitatZone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    waypoints = patrol_optimizer.generate_patrol_route(db, zone, max_waypoints=payload.max_waypoints)
    distance_km = patrol_optimizer.estimate_route_distance_km(zone.center_lat, zone.center_lon, waypoints)
    risk = patrol_optimizer.route_risk_score(waypoints)

    patrol = models.Patrol(
        zone_id=zone.id,
        scheduled_date=payload.scheduled_date,
        lead_ranger_id=payload.lead_ranger_id,
        team_size=payload.team_size,
        planned_distance_km=distance_km,
        risk_score=risk,
        status=models.PatrolStatus.PLANNED,
    )
    db.add(patrol)
    db.flush()

    for i, w in enumerate(waypoints, start=1):
        db.add(models.PatrolWaypoint(
            patrol_id=patrol.id,
            sequence=i,
            label=w["label"],
            latitude=w["latitude"],
            longitude=w["longitude"],
            priority_score=w["priority_score"],
        ))
    db.commit()
    db.refresh(patrol)
    return patrol


@router.patch("/patrols/{patrol_id}/status", response_model=schemas.PatrolOut)
def update_patrol_status(patrol_id: str, status: str, db: Session = Depends(get_db)):
    patrol = db.query(models.Patrol).filter(models.Patrol.id == patrol_id).first()
    if not patrol:
        raise HTTPException(status_code=404, detail="Patrol not found")
    try:
        patrol.status = models.PatrolStatus(status)
    except ValueError:
        valid = [s.value for s in models.PatrolStatus]
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    db.commit()
    db.refresh(patrol)
    return patrol
