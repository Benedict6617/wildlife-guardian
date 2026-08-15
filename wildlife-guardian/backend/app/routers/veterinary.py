from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["veterinary"])


@router.get("/vet-cases", response_model=List[schemas.VetCaseOut])
def list_vet_cases(status: Optional[str] = None, priority: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.VetCase)
    if status:
        try:
            q = q.filter(models.VetCase.status == models.VetCaseStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
    if priority:
        try:
            q = q.filter(models.VetCase.priority == models.VetCasePriority(priority))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority '{priority}'")
    return q.order_by(models.VetCase.reported_at.desc()).all()


@router.post("/vet-cases", response_model=schemas.VetCaseOut, status_code=201)
def report_vet_case(payload: schemas.VetCaseCreate, db: Session = Depends(get_db)):
    animal = db.query(models.Animal).filter(models.Animal.id == payload.animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    data = payload.model_dump()
    try:
        data["priority"] = models.VetCasePriority(data["priority"])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority value")
    case = models.VetCase(**data)
    db.add(case)
    animal.status = models.AnimalStatus.MEDICAL_CARE
    db.commit()
    db.refresh(case)
    return case


@router.patch("/vet-cases/{case_id}/status", response_model=schemas.VetCaseOut)
def update_vet_case_status(case_id: str, status: str, assigned_vet: Optional[str] = None, db: Session = Depends(get_db)):
    case = db.query(models.VetCase).filter(models.VetCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        new_status = models.VetCaseStatus(status)
    except ValueError:
        valid = [s.value for s in models.VetCaseStatus]
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    case.status = new_status
    if assigned_vet:
        case.assigned_vet = assigned_vet
    if new_status in (models.VetCaseStatus.RESOLVED, models.VetCaseStatus.DECEASED):
        case.resolved_at = datetime.utcnow()
        animal = db.query(models.Animal).filter(models.Animal.id == case.animal_id).first()
        if animal:
            animal.status = (
                models.AnimalStatus.ACTIVE if new_status == models.VetCaseStatus.RESOLVED
                else models.AnimalStatus.DECEASED
            )
    db.commit()
    db.refresh(case)
    return case
