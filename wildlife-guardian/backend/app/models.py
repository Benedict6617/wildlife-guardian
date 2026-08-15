"""
ORM models for the Wildlife Guardian platform.

Modules represented here:
  - Species tracking & GPS telemetry (Species, Animal, Collar, GPSPing)
  - Habitat & satellite monitoring (HabitatZone, SatelliteImage)
  - Threat detection (SensorNode, PoachingAlert, SnareDetection, DroneMission)
  - Ranger operations (Ranger, Patrol, PatrolWaypoint)
  - Veterinary logistics (VetCase)
  - Compliance (CITESPermit)
  - Community engagement (CommunityMember, SMSAlert)
  - Fundraising & donor transparency (Donor, Donation, Campaign)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean, Enum
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _enum_values(enum_cls):
    """Store the enum's .value (lowercase, API-matching) in the DB instead of
    SQLAlchemy's default of the member .name -- keeps raw DB rows readable
    and consistent with what the API returns."""
    return [e.value for e in enum_cls]


# ---------------------------------------------------------------------------
# Species & telemetry
# ---------------------------------------------------------------------------

class ConservationStatus(str, enum.Enum):
    LEAST_CONCERN = "least_concern"
    NEAR_THREATENED = "near_threatened"
    VULNERABLE = "vulnerable"
    ENDANGERED = "endangered"
    CRITICALLY_ENDANGERED = "critically_endangered"


class Species(Base):
    __tablename__ = "species"

    id = Column(String, primary_key=True, default=lambda: gen_id("SPC"))
    common_name = Column(String, nullable=False)
    scientific_name = Column(String, nullable=False)
    conservation_status = Column(Enum(ConservationStatus, values_callable=_enum_values), nullable=False)
    cites_appendix = Column(String, nullable=True)  # I, II, III
    population_estimate = Column(Integer, nullable=True)

    animals = relationship("Animal", back_populates="species")


class AnimalStatus(str, enum.Enum):
    ACTIVE = "active"
    UNDER_OBSERVATION = "under_observation"
    MEDICAL_CARE = "medical_care"
    DECEASED = "deceased"


class Animal(Base):
    __tablename__ = "animals"

    id = Column(String, primary_key=True, default=lambda: gen_id("ANM"))
    tag_name = Column(String, nullable=False)
    species_id = Column(String, ForeignKey("species.id"), nullable=False)
    sex = Column(String, nullable=True)
    estimated_age_years = Column(Integer, nullable=True)
    status = Column(Enum(AnimalStatus, values_callable=_enum_values), default=AnimalStatus.ACTIVE)
    home_zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=True)
    notes = Column(Text, nullable=True)

    species = relationship("Species", back_populates="animals")
    collar = relationship("Collar", back_populates="animal", uselist=False)
    vet_cases = relationship("VetCase", back_populates="animal")


class Collar(Base):
    __tablename__ = "collars"

    id = Column(String, primary_key=True, default=lambda: gen_id("COL"))
    device_serial = Column(String, unique=True, nullable=False)
    animal_id = Column(String, ForeignKey("animals.id"), unique=True, nullable=False)
    manufacturer = Column(String, default="Savanna Telemetrics")
    battery_pct = Column(Float, default=100.0)
    fix_interval_minutes = Column(Integer, default=30)
    installed_at = Column(DateTime, default=datetime.utcnow)
    last_fix_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    animal = relationship("Animal", back_populates="collar")
    pings = relationship("GPSPing", back_populates="collar", cascade="all, delete-orphan")


class GPSPing(Base):
    __tablename__ = "gps_pings"

    id = Column(String, primary_key=True, default=lambda: gen_id("PNG"))
    collar_id = Column(String, ForeignKey("collars.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmh = Column(Float, default=0.0)
    heading_deg = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    collar = relationship("Collar", back_populates="pings")


# ---------------------------------------------------------------------------
# Habitat & satellite monitoring
# ---------------------------------------------------------------------------

class HabitatZone(Base):
    __tablename__ = "habitat_zones"

    id = Column(String, primary_key=True, default=lambda: gen_id("ZON"))
    name = Column(String, nullable=False)
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    radius_km = Column(Float, default=5.0)
    water_index = Column(Float, default=0.5)   # 0-1, derived from satellite/IoT sensors
    forage_index = Column(Float, default=0.5)  # 0-1, vegetation greenness (NDVI proxy)
    risk_index = Column(Float, default=0.2)    # 0-1, poaching risk score
    notes = Column(Text, nullable=True)

    satellite_images = relationship("SatelliteImage", back_populates="zone")


class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id = Column(String, primary_key=True, default=lambda: gen_id("SAT"))
    zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="Sentinel-2 (simulated feed)")
    ndvi_score = Column(Float, nullable=True)   # vegetation health, -1 to 1
    surface_water_pct = Column(Float, nullable=True)
    anomaly_detected = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    zone = relationship("HabitatZone", back_populates="satellite_images")


# ---------------------------------------------------------------------------
# Threat detection
# ---------------------------------------------------------------------------

class SensorType(str, enum.Enum):
    ACOUSTIC = "acoustic"
    THERMAL_CAMERA = "thermal_camera"
    SEISMIC = "seismic"
    CAMERA_TRAP = "camera_trap"


class SensorNode(Base):
    __tablename__ = "sensor_nodes"

    id = Column(String, primary_key=True, default=lambda: gen_id("SEN"))
    node_code = Column(String, unique=True, nullable=False)
    sensor_type = Column(Enum(SensorType, values_callable=_enum_values), nullable=False)
    zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    battery_pct = Column(Float, default=100.0)
    is_online = Column(Boolean, default=True)
    installed_at = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("PoachingAlert", back_populates="sensor")


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"


class PoachingAlert(Base):
    __tablename__ = "poaching_alerts"

    id = Column(String, primary_key=True, default=lambda: gen_id("ALT"))
    sensor_id = Column(String, ForeignKey("sensor_nodes.id"), nullable=True)
    source = Column(String, default="sensor")  # sensor | drone | ranger_report
    alert_type = Column(String, nullable=False)  # gunshot, vehicle, human_intrusion, thermal_signature
    severity = Column(Enum(AlertSeverity, values_callable=_enum_values), default=AlertSeverity.MEDIUM)
    status = Column(Enum(AlertStatus, values_callable=_enum_values), default=AlertStatus.NEW)
    confidence_pct = Column(Float, default=70.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    dispatched_patrol_id = Column(String, ForeignKey("patrols.id"), nullable=True)

    sensor = relationship("SensorNode", back_populates="alerts")


class DroneMission(Base):
    __tablename__ = "drone_missions"

    id = Column(String, primary_key=True, default=lambda: gen_id("DRN"))
    mission_code = Column(String, unique=True, nullable=False)
    zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=True)
    pilot_name = Column(String, nullable=False)
    launched_at = Column(DateTime, default=datetime.utcnow)
    duration_minutes = Column(Integer, default=25)
    altitude_m = Column(Integer, default=120)
    status = Column(String, default="completed")  # planned, in_flight, completed, aborted
    snares_detected_count = Column(Integer, default=0)
    summary = Column(Text, nullable=True)


class SnareDetection(Base):
    __tablename__ = "snare_detections"

    id = Column(String, primary_key=True, default=lambda: gen_id("SNR"))
    mission_id = Column(String, ForeignKey("drone_missions.id"), nullable=True)
    detection_source = Column(String, default="drone_cv")  # drone_cv | camera_trap_cv
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    confidence_pct = Column(Float, default=80.0)
    detected_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending_removal")  # pending_removal, removed, false_positive
    cleared_by_ranger_id = Column(String, ForeignKey("rangers.id"), nullable=True)
    cleared_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Ranger operations
# ---------------------------------------------------------------------------

class Ranger(Base):
    __tablename__ = "rangers"

    id = Column(String, primary_key=True, default=lambda: gen_id("RNG"))
    badge_number = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    rank = Column(String, default="Ranger")
    station = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    is_active_duty = Column(Boolean, default=True)
    years_of_service = Column(Integer, default=1)


class PatrolStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Patrol(Base):
    __tablename__ = "patrols"

    id = Column(String, primary_key=True, default=lambda: gen_id("PTR"))
    zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=True)
    scheduled_date = Column(DateTime, nullable=False)
    status = Column(Enum(PatrolStatus, values_callable=_enum_values), default=PatrolStatus.PLANNED)
    lead_ranger_id = Column(String, ForeignKey("rangers.id"), nullable=True)
    team_size = Column(Integer, default=2)
    planned_distance_km = Column(Float, nullable=True)
    risk_score = Column(Float, default=0.0)  # output of optimizer, 0-1
    trigger_alert_id = Column(String, ForeignKey("poaching_alerts.id"), nullable=True)
    notes = Column(Text, nullable=True)

    waypoints = relationship("PatrolWaypoint", back_populates="patrol",
                              cascade="all, delete-orphan", order_by="PatrolWaypoint.sequence")


class PatrolWaypoint(Base):
    __tablename__ = "patrol_waypoints"

    id = Column(String, primary_key=True, default=lambda: gen_id("WPT"))
    patrol_id = Column(String, ForeignKey("patrols.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    label = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    priority_score = Column(Float, default=0.0)

    patrol = relationship("Patrol", back_populates="waypoints")


# ---------------------------------------------------------------------------
# Veterinary logistics
# ---------------------------------------------------------------------------

class VetCasePriority(str, enum.Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class VetCaseStatus(str, enum.Enum):
    REPORTED = "reported"
    TEAM_DISPATCHED = "team_dispatched"
    IN_TREATMENT = "in_treatment"
    RESOLVED = "resolved"
    DECEASED = "deceased"


class VetCase(Base):
    __tablename__ = "vet_cases"

    id = Column(String, primary_key=True, default=lambda: gen_id("VET"))
    animal_id = Column(String, ForeignKey("animals.id"), nullable=False)
    reported_at = Column(DateTime, default=datetime.utcnow)
    condition = Column(String, nullable=False)  # e.g. snare_injury, illness, birth_complication
    priority = Column(Enum(VetCasePriority, values_callable=_enum_values), default=VetCasePriority.URGENT)
    status = Column(Enum(VetCaseStatus, values_callable=_enum_values), default=VetCaseStatus.REPORTED)
    assigned_vet = Column(String, nullable=True)
    intervention_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    animal = relationship("Animal", back_populates="vet_cases")


# ---------------------------------------------------------------------------
# CITES compliance
# ---------------------------------------------------------------------------

class CITESPermitStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CITESPermit(Base):
    __tablename__ = "cites_permits"

    id = Column(String, primary_key=True, default=lambda: gen_id("CIT"))
    permit_number = Column(String, unique=True, nullable=False)
    species_id = Column(String, ForeignKey("species.id"), nullable=False)
    purpose = Column(String, nullable=False)  # scientific, translocation, seizure_disposal, captive_bred
    quantity = Column(Integer, default=1)
    unit_description = Column(String, default="live specimen")
    origin_country = Column(String, default="Kenya")
    destination_country = Column(String, nullable=False)
    issuing_authority = Column(String, default="Kenya Wildlife Service Management Authority")
    issue_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(Enum(CITESPermitStatus, values_callable=_enum_values), default=CITESPermitStatus.DRAFT)
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Community engagement
# ---------------------------------------------------------------------------

class CommunityMember(Base):
    __tablename__ = "community_members"

    id = Column(String, primary_key=True, default=lambda: gen_id("CMM"))
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    village = Column(String, nullable=True)
    role = Column(String, default="resident")  # resident, village_elder, scout_volunteer
    opted_in = Column(Boolean, default=True)
    zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=True)


class SMSAlert(Base):
    __tablename__ = "sms_alerts"

    id = Column(String, primary_key=True, default=lambda: gen_id("SMS"))
    category = Column(String, nullable=False)  # poaching_warning, wildlife_proximity, community_update
    message = Column(Text, nullable=False)
    recipient_count = Column(Integer, default=0)
    zone_id = Column(String, ForeignKey("habitat_zones.id"), nullable=True)
    related_alert_id = Column(String, ForeignKey("poaching_alerts.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivery_status = Column(String, default="delivered")  # queued, delivered, failed


# ---------------------------------------------------------------------------
# Fundraising & donor transparency
# ---------------------------------------------------------------------------

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: gen_id("CMP"))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    goal_amount_usd = Column(Float, nullable=False)
    raised_amount_usd = Column(Float, default=0.0)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    donations = relationship("Donation", back_populates="campaign")


class Donor(Base):
    __tablename__ = "donors"

    id = Column(String, primary_key=True, default=lambda: gen_id("DNR"))
    name = Column(String, nullable=False)
    donor_type = Column(String, default="individual")  # individual, corporate, foundation
    country = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_recurring_supporter = Column(Boolean, default=False)

    donations = relationship("Donation", back_populates="donor")


class Donation(Base):
    __tablename__ = "donations"

    id = Column(String, primary_key=True, default=lambda: gen_id("DON"))
    donor_id = Column(String, ForeignKey("donors.id"), nullable=False)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    amount_usd = Column(Float, nullable=False)
    donated_at = Column(DateTime, default=datetime.utcnow)
    allocation = Column(String, default="general_fund")  # ranger_ops, vet_care, tech_equipment, community
    is_public = Column(Boolean, default=True)  # donor consent to show on transparency dashboard

    donor = relationship("Donor", back_populates="donations")
    campaign = relationship("Campaign", back_populates="donations")
