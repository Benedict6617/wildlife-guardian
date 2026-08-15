from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import movement_predictor

router = APIRouter(prefix="/api/v1", tags=["tracking"])


@router.get("/species", response_model=List[schemas.SpeciesOut])
def list_species(db: Session = Depends(get_db)):
    return db.query(models.Species).all()


@router.get("/animals", response_model=List[schemas.AnimalOut])
def list_animals(
    species_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Animal)
    if species_id:
        q = q.filter(models.Animal.species_id == species_id)
    if status:
        try:
            q = q.filter(models.Animal.status == models.AnimalStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
    return q.all()


@router.get("/animals/{animal_id}", response_model=schemas.AnimalDetailOut)
def get_animal(animal_id: str, db: Session = Depends(get_db)):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    return animal


@router.get("/animals/{animal_id}/history", response_model=List[schemas.GPSPingOut])
def get_animal_history(
    animal_id: str,
    limit: int = Query(200, le=2000),
    db: Session = Depends(get_db),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal or not animal.collar:
        raise HTTPException(status_code=404, detail="No collar telemetry for this animal")
    pings = (
        db.query(models.GPSPing)
        .filter(models.GPSPing.collar_id == animal.collar.id)
        .order_by(models.GPSPing.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(pings))


@router.get("/animals/{animal_id}/predict", response_model=schemas.MovementPredictionOut)
def predict_movement(animal_id: str, db: Session = Depends(get_db)):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    prediction = movement_predictor.predict_next_location(db, animal)
    if not prediction:
        raise HTTPException(status_code=422, detail="Insufficient telemetry to generate a prediction")
    return prediction


@router.get("/collars", response_model=List[schemas.CollarOut])
def list_collars(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(models.Collar)
    if active_only:
        q = q.filter(models.Collar.is_active == True)  # noqa: E712
    return q.all()


@router.get("/tracking/live", response_model=List[schemas.GPSPingOut])
def live_positions(db: Session = Depends(get_db)):
    """Latest known fix per active collar -- powers the live map view."""
    collars = db.query(models.Collar).filter(models.Collar.is_active == True).all()  # noqa: E712
    latest = []
    for c in collars:
        if c.pings:
            latest.append(max(c.pings, key=lambda p: p.recorded_at))
    return latest


@router.get("/habitat-zones", response_model=List[schemas.HabitatZoneOut])
def list_habitat_zones(db: Session = Depends(get_db)):
    return db.query(models.HabitatZone).all()


@router.get("/habitat-zones/{zone_id}/satellite", response_model=List[schemas.SatelliteImageOut])
def zone_satellite_history(zone_id: str, db: Session = Depends(get_db)):
    zone = db.query(models.HabitatZone).filter(models.HabitatZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return (
        db.query(models.SatelliteImage)
        .filter(models.SatelliteImage.zone_id == zone_id)
        .order_by(models.SatelliteImage.captured_at.desc())
        .all()
    )
