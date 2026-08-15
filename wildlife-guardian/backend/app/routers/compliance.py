import os
import random
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.cites_pdf import generate_permit_pdf

router = APIRouter(prefix="/api/v1", tags=["compliance"])

GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_documents")
os.makedirs(GENERATED_DIR, exist_ok=True)


def _new_permit_number() -> str:
    return f"KE-CITES-{datetime.utcnow().year}-{random.randint(10000, 99999)}"


@router.get("/cites-permits", response_model=List[schemas.CITESPermitOut])
def list_permits(db: Session = Depends(get_db)):
    return db.query(models.CITESPermit).order_by(models.CITESPermit.issue_date.desc()).all()


@router.post("/cites-permits", response_model=schemas.CITESPermitOut, status_code=201)
def create_permit(payload: schemas.CITESPermitCreate, db: Session = Depends(get_db)):
    species = db.query(models.Species).filter(models.Species.id == payload.species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
    permit = models.CITESPermit(
        permit_number=_new_permit_number(),
        species_id=payload.species_id,
        purpose=payload.purpose,
        quantity=payload.quantity,
        unit_description=payload.unit_description,
        destination_country=payload.destination_country,
        expiry_date=datetime.utcnow() + timedelta(days=payload.expiry_days),
        status=models.CITESPermitStatus.ISSUED,
        notes=payload.notes,
    )
    db.add(permit)
    db.commit()
    db.refresh(permit)
    return permit


@router.get("/cites-permits/{permit_id}/pdf")
def download_permit_pdf(permit_id: str, db: Session = Depends(get_db)):
    permit = db.query(models.CITESPermit).filter(models.CITESPermit.id == permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")
    species = db.query(models.Species).filter(models.Species.id == permit.species_id).first()
    output_path = os.path.join(GENERATED_DIR, f"{permit.permit_number}.pdf")
    generate_permit_pdf(permit, species, output_path)
    return FileResponse(output_path, media_type="application/pdf", filename=f"{permit.permit_number}.pdf")
