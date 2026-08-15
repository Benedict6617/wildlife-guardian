"""Pydantic schemas. Read models use from_attributes for direct ORM serialization."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Species / Animals / Collars --------------------------------------------

class SpeciesOut(ORMBase):
    id: str
    common_name: str
    scientific_name: str
    conservation_status: str
    cites_appendix: Optional[str] = None
    population_estimate: Optional[int] = None


class AnimalOut(ORMBase):
    id: str
    tag_name: str
    species_id: str
    sex: Optional[str] = None
    estimated_age_years: Optional[int] = None
    status: str
    home_zone_id: Optional[str] = None
    notes: Optional[str] = None


class AnimalDetailOut(AnimalOut):
    species: SpeciesOut


class CollarOut(ORMBase):
    id: str
    device_serial: str
    animal_id: str
    battery_pct: float
    fix_interval_minutes: int
    last_fix_at: Optional[datetime] = None
    is_active: bool


class GPSPingOut(ORMBase):
    id: str
    collar_id: str
    latitude: float
    longitude: float
    speed_kmh: float
    heading_deg: float
    recorded_at: datetime


class MovementPredictionOut(BaseModel):
    animal_id: str
    predicted_latitude: float
    predicted_longitude: float
    predicted_zone_id: Optional[str]
    confidence_pct: float
    rationale: str


# --- Habitat / satellite ------------------------------------------------------

class HabitatZoneOut(ORMBase):
    id: str
    name: str
    center_lat: float
    center_lon: float
    radius_km: float
    water_index: float
    forage_index: float
    risk_index: float


class SatelliteImageOut(ORMBase):
    id: str
    zone_id: str
    captured_at: datetime
    source: str
    ndvi_score: Optional[float] = None
    surface_water_pct: Optional[float] = None
    anomaly_detected: bool
    notes: Optional[str] = None


# --- Threat detection ----------------------------------------------------------

class SensorNodeOut(ORMBase):
    id: str
    node_code: str
    sensor_type: str
    zone_id: Optional[str] = None
    latitude: float
    longitude: float
    battery_pct: float
    is_online: bool


class PoachingAlertOut(ORMBase):
    id: str
    sensor_id: Optional[str] = None
    source: str
    alert_type: str
    severity: str
    status: str
    confidence_pct: float
    latitude: float
    longitude: float
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    description: Optional[str] = None
    dispatched_patrol_id: Optional[str] = None


class PoachingAlertCreate(BaseModel):
    sensor_id: Optional[str] = None
    source: str = "sensor"
    alert_type: str
    severity: str = "medium"
    confidence_pct: float = 70.0
    latitude: float
    longitude: float
    description: Optional[str] = None


class AlertStatusUpdate(BaseModel):
    status: str


class DroneMissionOut(ORMBase):
    id: str
    mission_code: str
    zone_id: Optional[str] = None
    pilot_name: str
    launched_at: datetime
    duration_minutes: int
    altitude_m: int
    status: str
    snares_detected_count: int
    summary: Optional[str] = None


class SnareDetectionOut(ORMBase):
    id: str
    mission_id: Optional[str] = None
    detection_source: str
    latitude: float
    longitude: float
    confidence_pct: float
    detected_at: datetime
    status: str


# --- Ranger operations --------------------------------------------------------

class RangerOut(ORMBase):
    id: str
    badge_number: str
    full_name: str
    rank: str
    station: Optional[str] = None
    is_active_duty: bool
    years_of_service: int


class PatrolWaypointOut(ORMBase):
    sequence: int
    label: Optional[str] = None
    latitude: float
    longitude: float
    priority_score: float


class PatrolOut(ORMBase):
    id: str
    zone_id: Optional[str] = None
    scheduled_date: datetime
    status: str
    lead_ranger_id: Optional[str] = None
    team_size: int
    planned_distance_km: Optional[float] = None
    risk_score: float
    waypoints: List[PatrolWaypointOut] = []


class PatrolGenerateRequest(BaseModel):
    zone_id: str
    scheduled_date: datetime
    team_size: int = 3
    lead_ranger_id: Optional[str] = None
    max_waypoints: int = 6


# --- Veterinary -----------------------------------------------------------------

class VetCaseOut(ORMBase):
    id: str
    animal_id: str
    reported_at: datetime
    condition: str
    priority: str
    status: str
    assigned_vet: Optional[str] = None
    intervention_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VetCaseCreate(BaseModel):
    animal_id: str
    condition: str
    priority: str = "urgent"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    intervention_notes: Optional[str] = None


# --- CITES -------------------------------------------------------------------

class CITESPermitOut(ORMBase):
    id: str
    permit_number: str
    species_id: str
    purpose: str
    quantity: int
    unit_description: str
    origin_country: str
    destination_country: str
    issuing_authority: str
    issue_date: datetime
    expiry_date: Optional[datetime] = None
    status: str


class CITESPermitCreate(BaseModel):
    species_id: str
    purpose: str
    quantity: int = 1
    unit_description: str = "live specimen"
    destination_country: str
    expiry_days: int = 180
    notes: Optional[str] = None


# --- Community engagement -----------------------------------------------------

class CommunityMemberOut(ORMBase):
    id: str
    full_name: str
    phone_number: str
    village: Optional[str] = None
    role: str
    opted_in: bool


class SMSAlertOut(ORMBase):
    id: str
    category: str
    message: str
    recipient_count: int
    zone_id: Optional[str] = None
    sent_at: datetime
    delivery_status: str


class SMSBroadcastRequest(BaseModel):
    category: str
    message: str
    zone_id: Optional[str] = None
    related_alert_id: Optional[str] = None


# --- Fundraising ----------------------------------------------------------------

class CampaignOut(ORMBase):
    id: str
    name: str
    description: Optional[str] = None
    goal_amount_usd: float
    raised_amount_usd: float
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool


class DonorOut(ORMBase):
    id: str
    name: str
    donor_type: str
    country: Optional[str] = None
    is_recurring_supporter: bool


class DonationOut(ORMBase):
    id: str
    donor_id: str
    campaign_id: Optional[str] = None
    amount_usd: float
    donated_at: datetime
    allocation: str
    is_public: bool


class DonationCreate(BaseModel):
    donor_id: str
    campaign_id: Optional[str] = None
    amount_usd: float
    allocation: str = "general_fund"
    is_public: bool = True


class DashboardSummary(BaseModel):
    total_animals_tracked: int
    active_collars: int
    open_alerts: int
    critical_alerts_7d: int
    patrols_this_week: int
    snares_pending_removal: int
    total_raised_usd: float
    active_campaigns: int
    community_members_reached: int
