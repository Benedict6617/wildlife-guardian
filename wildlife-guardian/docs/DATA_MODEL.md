# Data Model

All models are defined in `backend/app/models.py`. IDs are prefixed, human-scannable strings (e.g. `ANM-4f2a9c1d` for an animal, `ALT-...` for an alert) generated client-side by the ORM rather than opaque auto-increment integers or raw UUIDs — easier to spot at a glance in logs, PDFs, and SMS text while still being globally unique.

## Entity groups

### Species & telemetry
- **Species** — common/scientific name, IUCN conservation status, CITES appendix, population estimate
- **Animal** — belongs to a Species, has a home HabitatZone, tracks status (active / under_observation / medical_care / deceased)
- **Collar** — one-to-one with Animal, tracks battery and fix interval
- **GPSPing** — timestamped lat/lon/speed/heading readings from a Collar

### Habitat & satellite
- **HabitatZone** — named area with center point, radius, and three 0–1 indices: `water_index`, `forage_index`, `risk_index`
- **SatelliteImage** — periodic capture per zone with NDVI score and surface water percentage

### Threat detection
- **SensorNode** — acoustic / thermal_camera / seismic / camera_trap device, located within a zone
- **PoachingAlert** — raised by a sensor, a drone, or a ranger field report; has severity and a status lifecycle (new → acknowledged → dispatched → resolved / false_alarm)
- **DroneMission** — a logged surveillance flight
- **SnareDetection** — a CV-flagged snare, linked to the mission that found it, with its own removal status

### Ranger operations
- **Ranger** — badge number, rank, station, years of service
- **Patrol** — scheduled zone patrol with a lead ranger, team size, and computed `risk_score`
- **PatrolWaypoint** — ordered stop within a Patrol, with a label and priority score explaining why the optimizer included it

### Veterinary
- **VetCase** — condition, priority (routine/urgent/emergency), status lifecycle, tied to an Animal

### Compliance
- **CITESPermit** — permit number, species, purpose, quantity, origin/destination country, issue/expiry dates

### Community engagement
- **CommunityMember** — name, phone, village, role, opt-in flag, associated zone
- **SMSAlert** — a sent broadcast: category, message, recipient count, delivery status

### Fundraising
- **Campaign** — named fundraising goal with a running `raised_amount_usd`
- **Donor** — individual / corporate / foundation, with country and recurring-supporter flag
- **Donation** — amount, allocation category, campaign link, and a public/private visibility flag for the transparency dashboard

## Entity relationship summary

```
Species 1───* Animal 1───1 Collar 1───* GPSPing
Animal *───1 HabitatZone
HabitatZone 1───* SatelliteImage
HabitatZone 1───* SensorNode 1───* PoachingAlert
HabitatZone 1───* DroneMission 1───* SnareDetection
HabitatZone 1───* Patrol 1───* PatrolWaypoint
Ranger 1───* Patrol
Animal 1───* VetCase
Species 1───* CITESPermit
HabitatZone 1───* CommunityMember
CommunityMember (implicit, by zone) ───* SMSAlert
Campaign 1───* Donation *───1 Donor
```

## Enum values

| Field | Values |
|---|---|
| `Animal.status` | active, under_observation, medical_care, deceased |
| `Species.conservation_status` | least_concern, near_threatened, vulnerable, endangered, critically_endangered |
| `SensorNode.sensor_type` | acoustic, thermal_camera, seismic, camera_trap |
| `PoachingAlert.severity` | low, medium, high, critical |
| `PoachingAlert.status` | new, acknowledged, dispatched, resolved, false_alarm |
| `Patrol.status` | planned, in_progress, completed, cancelled |
| `VetCase.priority` | routine, urgent, emergency |
| `VetCase.status` | reported, team_dispatched, in_treatment, resolved, deceased |
| `CITESPermit.status` | draft, issued, expired, revoked |

Enum columns store their lowercase `.value` (not the Python member name) in the database, so raw SQL queries and the API always show the same string — see the `values_callable` note in `app/models.py`.
