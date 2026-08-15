from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["fundraising"])


@router.get("/campaigns", response_model=List[schemas.CampaignOut])
def list_campaigns(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(models.Campaign)
    if active_only:
        q = q.filter(models.Campaign.is_active == True)  # noqa: E712
    return q.all()


@router.get("/donors", response_model=List[schemas.DonorOut])
def list_donors(db: Session = Depends(get_db)):
    return db.query(models.Donor).all()


@router.get("/donations", response_model=List[schemas.DonationOut])
def list_donations(campaign_id: Optional[str] = None, public_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(models.Donation)
    if campaign_id:
        q = q.filter(models.Donation.campaign_id == campaign_id)
    if public_only:
        q = q.filter(models.Donation.is_public == True)  # noqa: E712
    return q.order_by(models.Donation.donated_at.desc()).all()


@router.post("/donations", response_model=schemas.DonationOut, status_code=201)
def record_donation(payload: schemas.DonationCreate, db: Session = Depends(get_db)):
    donor = db.query(models.Donor).filter(models.Donor.id == payload.donor_id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    donation = models.Donation(**payload.model_dump())
    db.add(donation)

    if payload.campaign_id:
        campaign = db.query(models.Campaign).filter(models.Campaign.id == payload.campaign_id).first()
        if campaign:
            campaign.raised_amount_usd += payload.amount_usd

    db.commit()
    db.refresh(donation)
    return donation


@router.get("/fundraising/allocation-breakdown")
def allocation_breakdown(db: Session = Depends(get_db)):
    """Sum of public donations by program allocation, for the transparency dashboard."""
    donations = db.query(models.Donation).filter(models.Donation.is_public == True).all()  # noqa: E712
    breakdown = {}
    for d in donations:
        breakdown[d.allocation] = breakdown.get(d.allocation, 0.0) + d.amount_usd
    return {k: round(v, 2) for k, v in sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)}
