"""
Ranger patrol route optimization.

Approach
--------
This is a deliberately transparent, explainable heuristic rather than a
black-box solver, which matters for field teams who need to trust and
override routes:

1. Build a candidate waypoint pool from three risk signals inside the zone:
     - unresolved poaching alerts (highest weight, recency-decayed)
     - offline/low-battery sensor nodes (need physical inspection)
     - pending snare detections awaiting removal
2. Score each candidate by severity/urgency and pick the top N.
3. Sequence the chosen waypoints with a nearest-neighbor walk starting from
   the ranger station (zone center), which approximates a short total-travel
   route -- a reasonable stand-in for a full vehicle-routing solver (e.g.
   OR-Tools) at small-conservancy scale (dozens of waypoints, not thousands).

Swap `_nearest_neighbor_order` for an OR-Tools VRP call if/when patrol areas
grow large enough that tour quality starts to matter more than latency.
"""
import math
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models

SEVERITY_WEIGHT = {"low": 1.0, "medium": 2.0, "high": 3.5, "critical": 5.0}


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _recency_decay(ts: datetime, half_life_hours: float = 48.0) -> float:
    age_hours = max((datetime.utcnow() - ts).total_seconds() / 3600.0, 0.0)
    return 0.5 ** (age_hours / half_life_hours)


def _nearest_neighbor_order(start_lat, start_lon, candidates: List[dict]) -> List[dict]:
    remaining = candidates.copy()
    ordered = []
    cur_lat, cur_lon = start_lat, start_lon
    while remaining:
        remaining.sort(key=lambda c: _haversine_km(cur_lat, cur_lon, c["latitude"], c["longitude"]))
        nxt = remaining.pop(0)
        ordered.append(nxt)
        cur_lat, cur_lon = nxt["latitude"], nxt["longitude"]
    return ordered


def generate_patrol_route(
    db: Session,
    zone: models.HabitatZone,
    max_waypoints: int = 6,
    lookback_days: int = 10,
) -> List[dict]:
    """Return an ordered list of waypoint dicts: label, lat, lon, priority_score."""
    since = datetime.utcnow() - timedelta(days=lookback_days)
    candidates = []

    open_statuses = [models.AlertStatus.NEW, models.AlertStatus.ACKNOWLEDGED, models.AlertStatus.DISPATCHED]
    alerts = (
        db.query(models.PoachingAlert)
        .filter(
            models.PoachingAlert.detected_at >= since,
            models.PoachingAlert.status.in_(open_statuses),
        )
        .all()
    )
    for a in alerts:
        dist = _haversine_km(zone.center_lat, zone.center_lon, a.latitude, a.longitude)
        if dist <= zone.radius_km * 1.5:
            severity_key = a.severity.value if hasattr(a.severity, "value") else a.severity
            score = SEVERITY_WEIGHT.get(severity_key, 1.0) * _recency_decay(a.detected_at)
            candidates.append({
                "label": f"Investigate {a.alert_type.replace('_', ' ')} alert",
                "latitude": a.latitude,
                "longitude": a.longitude,
                "priority_score": round(score, 3),
                "kind": "alert",
            })

    sensors = (
        db.query(models.SensorNode)
        .filter(models.SensorNode.zone_id == zone.id)
        .filter((models.SensorNode.is_online == False) | (models.SensorNode.battery_pct < 25))  # noqa: E712
        .all()
    )
    for s in sensors:
        urgency = 1.5 if not s.is_online else 1.0
        candidates.append({
            "label": f"Service sensor {s.node_code}",
            "latitude": s.latitude,
            "longitude": s.longitude,
            "priority_score": round(urgency, 3),
            "kind": "maintenance",
        })

    snares = (
        db.query(models.SnareDetection)
        .filter(models.SnareDetection.status == "pending_removal")
        .all()
    )
    for sn in snares:
        dist = _haversine_km(zone.center_lat, zone.center_lon, sn.latitude, sn.longitude)
        if dist <= zone.radius_km * 1.5:
            score = 2.5 * (sn.confidence_pct / 100.0)
            candidates.append({
                "label": "Remove detected snare",
                "latitude": sn.latitude,
                "longitude": sn.longitude,
                "priority_score": round(score, 3),
                "kind": "snare_removal",
            })

    # Always include at least one routine perimeter checkpoint so a patrol
    # is generated even in a quiet week.
    if not candidates:
        candidates.append({
            "label": "Routine perimeter checkpoint",
            "latitude": zone.center_lat + 0.01,
            "longitude": zone.center_lon + 0.01,
            "priority_score": 0.5,
            "kind": "routine",
        })

    candidates.sort(key=lambda c: c["priority_score"], reverse=True)
    top = candidates[:max_waypoints]
    ordered = _nearest_neighbor_order(zone.center_lat, zone.center_lon, top)
    return ordered


def estimate_route_distance_km(start_lat, start_lon, waypoints: List[dict]) -> float:
    total = 0.0
    cur_lat, cur_lon = start_lat, start_lon
    for w in waypoints:
        total += _haversine_km(cur_lat, cur_lon, w["latitude"], w["longitude"])
        cur_lat, cur_lon = w["latitude"], w["longitude"]
    return round(total, 2)


def route_risk_score(waypoints: List[dict]) -> float:
    if not waypoints:
        return 0.0
    avg = sum(w["priority_score"] for w in waypoints) / len(waypoints)
    return round(min(avg / 5.0, 1.0), 3)
