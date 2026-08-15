"""
Populates the database with a realistic, internally-consistent sample dataset
for a fictional conservancy: Northern Rift Conservancy, Laikipia County,
Kenya (~0.30N, 36.80E). All names, permit numbers, and identifiers below are
synthetic and generated for demonstration purposes only.

Run with:
    python -m app.seed
"""
import random
from datetime import datetime, timedelta

from app.database import Base, engine, SessionLocal
from app import models

random.seed(42)

# Conservancy center used as the ranger HQ reference point.
HQ_LAT, HQ_LON = 0.2965, 36.8219


def jitter(lat, lon, km_radius):
    """Small random offset in degrees, approximating a km radius."""
    deg = km_radius / 111.0
    return lat + random.uniform(-deg, deg), lon + random.uniform(-deg, deg)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed():
    reset_db()
    db = SessionLocal()

    # --- Species -------------------------------------------------------
    species_defs = [
        ("African Elephant", "Loxodonta africana", models.ConservationStatus.ENDANGERED, "I", 415000),
        ("Black Rhinoceros", "Diceros bicornis", models.ConservationStatus.CRITICALLY_ENDANGERED, "I", 6195),
        ("Grevy's Zebra", "Equus grevyi", models.ConservationStatus.ENDANGERED, "I", 2812),
        ("African Wild Dog", "Lycaon pictus", models.ConservationStatus.ENDANGERED, "II", 6600),
        ("Reticulated Giraffe", "Giraffa reticulata", models.ConservationStatus.VULNERABLE, "II", 15985),
    ]
    species = {}
    for name, sci, status, appendix, pop in species_defs:
        s = models.Species(common_name=name, scientific_name=sci, conservation_status=status,
                            cites_appendix=appendix, population_estimate=pop)
        db.add(s)
        species[name] = s
    db.flush()

    # --- Habitat zones ---------------------------------------------------
    zone_defs = [
        ("Ewaso Riverline Corridor", 0.315, 36.845, 6.0, 0.82, 0.61, 0.35),
        ("Mukutan Escarpment", 0.271, 36.789, 5.5, 0.38, 0.55, 0.55),
        ("Sosian Plains", 0.331, 36.762, 8.0, 0.44, 0.71, 0.20),
        ("Segera Woodland", 0.256, 36.848, 4.5, 0.51, 0.66, 0.42),
        ("Northern Buffer Zone", 0.349, 36.812, 7.0, 0.30, 0.40, 0.68),
    ]
    zones = {}
    for name, lat, lon, radius, water, forage, risk in zone_defs:
        z = models.HabitatZone(name=name, center_lat=lat, center_lon=lon, radius_km=radius,
                                water_index=water, forage_index=forage, risk_index=risk)
        db.add(z)
        zones[name] = z
    db.flush()

    # --- Satellite imagery (last 6 biweekly captures per zone) --------
    for z in zones.values():
        for i in range(6):
            captured = datetime.utcnow() - timedelta(days=14 * (6 - i))
            ndvi = round(0.2 + z.forage_index * 0.5 + random.uniform(-0.05, 0.05), 3)
            water_pct = round(z.water_index * 30 + random.uniform(-3, 3), 1)
            db.add(models.SatelliteImage(
                zone_id=z.id, captured_at=captured, source="Sentinel-2 (simulated feed)",
                ndvi_score=ndvi, surface_water_pct=max(water_pct, 0),
                anomaly_detected=(i == 5 and z.name == "Northern Buffer Zone"),
                notes="Vegetation greening consistent with recent rainfall." if ndvi > 0.4
                      else "Below-average vegetation index; monitor forage stress.",
            ))
    db.flush()

    # --- Animals + collars + GPS history --------------------------------
    animal_defs = [
        ("Kanini", "African Elephant", "F", 34, "Ewaso Riverline Corridor"),
        ("Tembo Jr", "African Elephant", "M", 12, "Ewaso Riverline Corridor"),
        ("Amara", "African Elephant", "F", 28, "Segera Woodland"),
        ("Kifaru One", "Black Rhinoceros", "M", 9, "Mukutan Escarpment"),
        ("Nyota", "Black Rhinoceros", "F", 15, "Mukutan Escarpment"),
        ("Punda Milia", "Grevy's Zebra", "F", 6, "Sosian Plains"),
        ("Haraka", "Grevy's Zebra", "M", 4, "Sosian Plains"),
        ("Simba Mdogo", "African Wild Dog", "M", 3, "Segera Woodland"),
        ("Pack Alpha", "African Wild Dog", "F", 5, "Segera Woodland"),
        ("Twiga Tall", "Reticulated Giraffe", "M", 11, "Northern Buffer Zone"),
        ("Twiga Pili", "Reticulated Giraffe", "F", 8, "Sosian Plains"),
        ("Kifaru Two", "Black Rhinoceros", "M", 21, "Mukutan Escarpment"),
    ]

    animals = []
    for i, (tag, sp_name, sex, age, home_zone) in enumerate(animal_defs):
        zone = zones[home_zone]
        animal = models.Animal(
            tag_name=tag, species_id=species[sp_name].id, sex=sex,
            estimated_age_years=age, status=models.AnimalStatus.ACTIVE, home_zone_id=zone.id,
        )
        db.add(animal)
        db.flush()

        collar = models.Collar(
            device_serial=f"SVT-{2000 + i:04d}", animal_id=animal.id,
            battery_pct=round(random.uniform(55, 100), 1), fix_interval_minutes=30,
            installed_at=datetime.utcnow() - timedelta(days=random.randint(90, 400)),
        )
        db.add(collar)
        db.flush()

        # 14 days of history, 8 fixes/day, random-walking around the home zone
        lat, lon = jitter(zone.center_lat, zone.center_lon, zone.radius_km * 0.5)
        last_time = None
        for day in range(14, 0, -1):
            for fix in range(8):
                ts = datetime.utcnow() - timedelta(days=day, hours=(24 - fix * 3))
                lat, lon = jitter(lat, lon, 0.8)
                ping = models.GPSPing(
                    collar_id=collar.id, latitude=round(lat, 5), longitude=round(lon, 5),
                    speed_kmh=round(random.uniform(0, 6.5), 1), heading_deg=round(random.uniform(0, 359), 1),
                    recorded_at=ts,
                )
                db.add(ping)
                last_time = ts
        collar.last_fix_at = last_time
        animals.append(animal)
    db.flush()

    # --- Sensor nodes -----------------------------------------------------
    sensor_types = [models.SensorType.ACOUSTIC, models.SensorType.THERMAL_CAMERA,
                     models.SensorType.SEISMIC, models.SensorType.CAMERA_TRAP]
    sensors = []
    node_num = 1
    for zone in zones.values():
        for _ in range(3):
            stype = random.choice(sensor_types)
            lat, lon = jitter(zone.center_lat, zone.center_lon, zone.radius_km * 0.6)
            s = models.SensorNode(
                node_code=f"NODE-{node_num:03d}", sensor_type=stype, zone_id=zone.id,
                latitude=round(lat, 5), longitude=round(lon, 5),
                battery_pct=round(random.uniform(15, 100), 1),
                is_online=random.random() > 0.12,
                installed_at=datetime.utcnow() - timedelta(days=random.randint(30, 500)),
            )
            db.add(s)
            sensors.append(s)
            node_num += 1
    db.flush()

    # --- Rangers ------------------------------------------------------------
    ranger_names = [
        "James Lekurruki", "Grace Nasieku", "Peter Cheruiyot", "Mary Wanjiru",
        "Daniel Lemomo", "Sarah Chepkoech", "Joseph Mwangi", "Ann Naisula",
        "Kevin Kiptoo", "Florence Achieng",
    ]
    stations = ["Ewaso Gate HQ", "Mukutan Outpost", "Sosian Ranger Camp", "Segera Field Station"]
    rangers = []
    for i, name in enumerate(ranger_names):
        r = models.Ranger(
            badge_number=f"NRC-{100 + i}", full_name=name,
            rank=random.choice(["Ranger", "Senior Ranger", "Corporal", "Sergeant"]),
            station=random.choice(stations), phone_number=f"+2547{random.randint(10000000, 99999999)}",
            is_active_duty=True, years_of_service=random.randint(1, 18),
        )
        db.add(r)
        rangers.append(r)
    db.flush()

    # --- Poaching alerts --------------------------------------------------
    alert_types = ["gunshot", "vehicle_intrusion", "human_intrusion", "thermal_signature", "fence_breach"]
    severities = [models.AlertSeverity.LOW, models.AlertSeverity.MEDIUM,
                  models.AlertSeverity.HIGH, models.AlertSeverity.CRITICAL]
    alerts = []
    for i in range(18):
        sensor = random.choice(sensors)
        zone = next(z for z in zones.values() if z.id == sensor.zone_id) if sensor.zone_id else random.choice(list(zones.values()))
        lat, lon = jitter(sensor.latitude, sensor.longitude, 1.2)
        severity = random.choices(severities, weights=[35, 30, 22, 13])[0]
        detected_at = datetime.utcnow() - timedelta(days=random.randint(0, 28), hours=random.randint(0, 23))
        status = random.choices(
            [models.AlertStatus.NEW, models.AlertStatus.ACKNOWLEDGED, models.AlertStatus.DISPATCHED,
             models.AlertStatus.RESOLVED, models.AlertStatus.FALSE_ALARM],
            weights=[15, 15, 15, 40, 15])[0]
        a = models.PoachingAlert(
            sensor_id=sensor.id, source="sensor", alert_type=random.choice(alert_types),
            severity=severity, status=status, confidence_pct=round(random.uniform(55, 98), 1),
            latitude=round(lat, 5), longitude=round(lon, 5), detected_at=detected_at,
            resolved_at=detected_at + timedelta(hours=random.randint(1, 30)) if status == models.AlertStatus.RESOLVED else None,
            description=f"{sensor.sensor_type.value.replace('_', ' ').title()} node {sensor.node_code} flagged a "
                        f"{severity.value} confidence event near {zone.name}.",
        )
        db.add(a)
        alerts.append(a)
    db.flush()

    # --- Drone missions + snare detections ---------------------------------
    pilots = ["Cpl. Lemomo", "Sgt. Chepkoech", "Ranger Mwangi"]
    missions = []
    for i in range(9):
        zone = random.choice(list(zones.values()))
        launched = datetime.utcnow() - timedelta(days=random.randint(0, 21))
        snare_count = random.choices([0, 1, 2, 3], weights=[45, 30, 15, 10])[0]
        m = models.DroneMission(
            mission_code=f"UAV-{2026}{i:03d}", zone_id=zone.id, pilot_name=random.choice(pilots),
            launched_at=launched, duration_minutes=random.randint(18, 40), altitude_m=random.choice([80, 100, 120, 150]),
            status="completed", snares_detected_count=snare_count,
            summary=f"Perimeter sweep of {zone.name}; {snare_count} snare-pattern object(s) flagged for ground verification.",
        )
        db.add(m)
        db.flush()
        missions.append(m)
        for _ in range(snare_count):
            lat, lon = jitter(zone.center_lat, zone.center_lon, zone.radius_km * 0.7)
            db.add(models.SnareDetection(
                mission_id=m.id, detection_source="drone_cv", latitude=round(lat, 5), longitude=round(lon, 5),
                confidence_pct=round(random.uniform(58, 95), 1), detected_at=launched + timedelta(minutes=random.randint(1, 35)),
                status=random.choices(["pending_removal", "removed", "false_positive"], weights=[45, 45, 10])[0],
            ))
    db.flush()

    # --- Patrols with waypoints ----------------------------------------------
    open_alerts = [a for a in alerts if a.status in (models.AlertStatus.NEW, models.AlertStatus.ACKNOWLEDGED, models.AlertStatus.DISPATCHED)]
    for i in range(7):
        zone = random.choice(list(zones.values()))
        scheduled = datetime.utcnow() - timedelta(days=random.randint(-3, 10))
        status = models.PatrolStatus.COMPLETED if scheduled < datetime.utcnow() else models.PatrolStatus.PLANNED
        p = models.Patrol(
            zone_id=zone.id, scheduled_date=scheduled, status=status,
            lead_ranger_id=random.choice(rangers).id, team_size=random.randint(2, 5),
            planned_distance_km=round(random.uniform(6, 22), 1), risk_score=round(random.uniform(0.1, 0.9), 2),
            notes="Auto-generated from optimizer during seeding; prioritized by nearby alert density.",
        )
        db.add(p)
        db.flush()
        for seq in range(1, random.randint(3, 5) + 1):
            lat, lon = jitter(zone.center_lat, zone.center_lon, zone.radius_km * 0.7)
            db.add(models.PatrolWaypoint(
                patrol_id=p.id, sequence=seq, label=random.choice(
                    ["Investigate alert cluster", "Service sensor node", "Remove detected snare", "Routine perimeter checkpoint"]
                ), latitude=round(lat, 5), longitude=round(lon, 5), priority_score=round(random.uniform(0.3, 4.5), 2),
            ))
    db.flush()

    # --- Veterinary cases ------------------------------------------------------
    zones_by_id = {z.id: z for z in zones.values()}
    conditions = ["snare_injury", "suspected_poisoning", "birth_complication", "respiratory_illness", "old_wound_infection"]
    for i in range(6):
        animal = random.choice(animals)
        reported = datetime.utcnow() - timedelta(days=random.randint(0, 60))
        priority = random.choices(
            [models.VetCasePriority.ROUTINE, models.VetCasePriority.URGENT, models.VetCasePriority.EMERGENCY],
            weights=[30, 45, 25])[0]
        status = random.choices(
            [models.VetCaseStatus.REPORTED, models.VetCaseStatus.TEAM_DISPATCHED,
             models.VetCaseStatus.IN_TREATMENT, models.VetCaseStatus.RESOLVED],
            weights=[15, 15, 20, 50])[0]
        db.add(models.VetCase(
            animal_id=animal.id, reported_at=reported, condition=random.choice(conditions),
            priority=priority, status=status, assigned_vet="Dr. Wanjiku Kamau, KWS Veterinary Unit",
            intervention_notes="Field immobilization and treatment completed; follow-up monitoring via collar telemetry."
            if status == models.VetCaseStatus.RESOLVED else "Case under active management.",
            resolved_at=reported + timedelta(days=random.randint(1, 5)) if status == models.VetCaseStatus.RESOLVED else None,
            latitude=zones_by_id[animal.home_zone_id].center_lat if animal.home_zone_id in zones_by_id else None,
            longitude=zones_by_id[animal.home_zone_id].center_lon if animal.home_zone_id in zones_by_id else None,
        ))
    db.flush()

    # --- CITES permits -------------------------------------------------------
    permit_defs = [
        ("Reticulated Giraffe", "translocation", 4, "live specimen (translocation group)", "Tanzania"),
        ("Black Rhinoceros", "scientific", 1, "biological sample (DNA/horn shaving)", "South Africa"),
        ("African Elephant", "seizure_disposal", 12, "kg raw ivory (recovered from seizure)", "Kenya (domestic disposal)"),
        ("African Wild Dog", "captive_bred", 2, "live specimen (captive-bred, breeding program)", "Rwanda"),
    ]
    for sp_name, purpose, qty, unit, dest in permit_defs:
        issue = datetime.utcnow() - timedelta(days=random.randint(5, 200))
        db.add(models.CITESPermit(
            permit_number=f"KE-CITES-{issue.year}-{random.randint(10000, 99999)}",
            species_id=species[sp_name].id, purpose=purpose, quantity=qty, unit_description=unit,
            destination_country=dest, issue_date=issue, expiry_date=issue + timedelta(days=180),
            status=models.CITESPermitStatus.ISSUED,
            notes="Issued in coordination with the national Wildlife Management Authority.",
        ))
    db.flush()

    # --- Community members + SMS alerts ------------------------------------
    villages = ["Kimanjo", "Ilingwesi", "Nkoteiya", "Mugie", "Naibunga"]
    first_names = ["Josephine", "Samuel", "Rebecca", "Moses", "Esther", "Francis", "Beatrice", "Isaac",
                   "Lucy", "Stephen", "Margaret", "Paul", "Agnes", "David", "Consolata", "John",
                   "Purity", "Elijah", "Winnie", "Boniface"]
    zone_list = list(zones.values())
    members = []
    for i, fname in enumerate(first_names):
        m = models.CommunityMember(
            full_name=f"{fname} {'Lekerian' if i % 3 == 0 else 'Nampaso' if i % 3 == 1 else 'Salau'}",
            phone_number=f"+2547{random.randint(10000000, 99999999)}",
            village=random.choice(villages), role=random.choices(
                ["resident", "village_elder", "scout_volunteer"], weights=[70, 15, 15])[0],
            opted_in=True, zone_id=random.choice(zone_list).id,
        )
        db.add(m)
        members.append(m)
    db.flush()

    sms_categories = ["poaching_warning", "wildlife_proximity", "community_update"]
    sms_messages = {
        "poaching_warning": "ALERT: Suspicious activity reported near {zone}. Avoid the area and report sightings to the ranger hotline.",
        "wildlife_proximity": "Notice: Elephant herd moving near {zone} grazing paths this evening. Keep livestock enclosed.",
        "community_update": "Northern Rift Conservancy update: water point repairs at {zone} completed this week.",
    }
    for i in range(10):
        cat = random.choice(sms_categories)
        zone = random.choice(zone_list)
        sent = datetime.utcnow() - timedelta(days=random.randint(0, 25))
        db.add(models.SMSAlert(
            category=cat, message=sms_messages[cat].format(zone=zone.name),
            recipient_count=random.randint(30, 120), zone_id=zone.id, sent_at=sent, delivery_status="delivered",
        ))
    db.flush()

    # --- Donors, campaigns, donations ------------------------------------------
    campaign_defs = [
        ("Collar the Herd 2026", "Fund 15 new GPS satellite collars for elephant matriarch tracking.", 45000),
        ("Ranger Ops Sustainment", "Cover fuel, equipment, and stipends for the anti-poaching patrol unit.", 80000),
        ("Rhino Sanctuary Expansion", "Extend the predator-proof sanctuary fence line by 12km.", 120000),
    ]
    campaigns = []
    for name, desc, goal in campaign_defs:
        c = models.Campaign(name=name, description=desc, goal_amount_usd=goal, raised_amount_usd=0.0,
                             start_date=datetime.utcnow() - timedelta(days=random.randint(30, 150)), is_active=True)
        db.add(c)
        campaigns.append(c)
    db.flush()

    donor_defs = [
        ("Rift Valley Wildlife Trust", "foundation", "Kenya"),
        ("Solveig & Anders Berg", "individual", "Norway"),
        ("Acacia Safaris Ltd", "corporate", "Kenya"),
        ("Global Species Alliance", "foundation", "United States"),
        ("Thomas Whitfield", "individual", "United Kingdom"),
        ("Nairobi Tech for Good", "corporate", "Kenya"),
        ("Chen Wei", "individual", "Singapore"),
        ("Savanna Conservation Fund", "foundation", "Netherlands"),
        ("Amina Yusuf", "individual", "Kenya"),
        ("Highland Coffee Cooperative", "corporate", "Kenya"),
        ("Laura Fitzgerald", "individual", "Ireland"),
        ("Pangea Earth Foundation", "foundation", "Switzerland"),
    ]
    donors = []
    for name, dtype, country in donor_defs:
        d = models.Donor(name=name, donor_type=dtype, country=country,
                          is_recurring_supporter=random.random() > 0.6)
        db.add(d)
        donors.append(d)
    db.flush()

    allocations = ["ranger_ops", "vet_care", "tech_equipment", "community", "general_fund"]
    for i in range(35):
        donor = random.choice(donors)
        campaign = random.choice(campaigns + [None, None])  # some general/unrestricted gifts
        amount = round(random.choice([50, 100, 250, 500, 1000, 2500, 5000, 10000]) * random.uniform(0.8, 1.2), 2)
        donation = models.Donation(
            donor_id=donor.id, campaign_id=campaign.id if campaign else None, amount_usd=amount,
            donated_at=datetime.utcnow() - timedelta(days=random.randint(0, 180)),
            allocation=random.choice(allocations), is_public=random.random() > 0.15,
        )
        db.add(donation)
        if campaign:
            campaign.raised_amount_usd += amount
    db.commit()

    print("Seed complete:")
    print(f"  species={len(species)} zones={len(zones)} animals={len(animals)} sensors={len(sensors)}")
    print(f"  rangers={len(rangers)} alerts={len(alerts)} drone_missions={len(missions)}")
    print(f"  donors={len(donors)} campaigns={len(campaigns)} community_members={len(members)}")

    db.close()


if __name__ == "__main__":
    seed()
