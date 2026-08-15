"""
Predicts an animal's next likely location.

Heuristic model (documented, not a mystery black box):
  - Start from the animal's most recent GPS fix.
  - Consider habitat zones within a species-appropriate travel radius.
  - Score each candidate zone as a weighted combination of:
        water_index, forage_index, and an inverse-distance travel cost.
  - Pull the prediction toward the highest-scoring zone's center, capped by
    a max daily displacement so predictions stay physically plausible.

This mirrors the real driver of ungulate/elephant movement (resource
availability) without requiring a trained ML model, so it stays inspectable
and easy to recalibrate per-species. Swap in a trained trajectory model
(e.g. an LSTM over historical pings) as telemetry history accumulates.
"""
import math
from typing import Optional

from sqlalchemy.orm import Session

from app import models

# Rough max daily displacement by species class, in km. Falls back to 8km.
MAX_DAILY_KM = {
    "African Elephant": 15.0,
    "Black Rhinoceros": 8.0,
    "Grevy's Zebra": 20.0,
    "African Wild Dog": 25.0,
}


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def predict_next_location(db: Session, animal: models.Animal) -> Optional[dict]:
    if not animal.collar or not animal.collar.pings:
        return None

    last_ping = max(animal.collar.pings, key=lambda p: p.recorded_at)
    zones = db.query(models.HabitatZone).all()
    if not zones:
        return None

    max_km = MAX_DAILY_KM.get(animal.species.common_name if animal.species else "", 8.0)

    best_zone = None
    best_score = -1.0
    for z in zones:
        dist = _haversine_km(last_ping.latitude, last_ping.longitude, z.center_lat, z.center_lon)
        travel_cost = 1.0 / (1.0 + dist / max(max_km, 1.0))
        resource_score = 0.6 * z.water_index + 0.4 * z.forage_index
        score = 0.65 * resource_score + 0.35 * travel_cost
        if score > best_score:
            best_score = score
            best_zone = z

    if best_zone is None:
        return None

    dist_to_zone = _haversine_km(
        last_ping.latitude, last_ping.longitude, best_zone.center_lat, best_zone.center_lon
    )
    step_km = min(max_km, dist_to_zone)
    if dist_to_zone == 0:
        pred_lat, pred_lon = last_ping.latitude, last_ping.longitude
    else:
        frac = step_km / dist_to_zone
        pred_lat = last_ping.latitude + (best_zone.center_lat - last_ping.latitude) * frac
        pred_lon = last_ping.longitude + (best_zone.center_lon - last_ping.longitude) * frac

    confidence = round(min(60 + best_score * 35, 95), 1)
    rationale = (
        f"Moving toward '{best_zone.name}' (water index {best_zone.water_index:.2f}, "
        f"forage index {best_zone.forage_index:.2f}); capped at {max_km:.0f} km/day "
        f"for {animal.species.common_name if animal.species else 'this species'}."
    )

    return {
        "animal_id": animal.id,
        "predicted_latitude": round(pred_lat, 5),
        "predicted_longitude": round(pred_lon, 5),
        "predicted_zone_id": best_zone.id,
        "confidence_pct": confidence,
        "rationale": rationale,
    }
