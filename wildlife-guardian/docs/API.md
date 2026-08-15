# API Reference

Full interactive documentation (auto-generated from the FastAPI schema, with request/response models and a "Try it out" console) is available at **`/docs`** (Swagger UI) or **`/redoc`** whenever the backend is running. This document is a quick-scan summary organized by domain; treat `/docs` as the source of truth.

Base URL: `http://localhost:8000/api/v1` (or your deployed API host).

## Tracking & habitat

| Method | Path | Description |
|---|---|---|
| GET | `/species` | List all tracked species |
| GET | `/animals` | List animals, optional `species_id` / `status` filters |
| GET | `/animals/{id}` | Animal detail including species info |
| GET | `/animals/{id}/history` | GPS ping history, optional `limit` |
| GET | `/animals/{id}/predict` | Predicted next location (water/forage-driven) |
| GET | `/collars` | List collars, optional `active_only` |
| GET | `/tracking/live` | Latest fix per active collar |
| GET | `/habitat-zones` | List habitat zones with water/forage/risk indices |
| GET | `/habitat-zones/{id}/satellite` | Satellite imagery history for a zone |

## Threat detection & drones

| Method | Path | Description |
|---|---|---|
| GET | `/sensors` | List sensor nodes, optional `online_only` |
| GET | `/alerts` | List poaching alerts, filters: `status`, `severity`, `days` |
| POST | `/alerts` | Log a new alert (sensor-triggered or manual ranger report) |
| PATCH | `/alerts/{id}/status` | Update alert status (new → acknowledged → dispatched → resolved/false_alarm) |
| GET | `/drone-missions` | List logged drone surveillance missions |
| GET | `/snares` | List snare detections, optional `status` filter |
| PATCH | `/snares/{id}/clear` | Mark a snare as removed, optionally recording the clearing ranger |

## Ranger patrols

| Method | Path | Description |
|---|---|---|
| GET | `/rangers` | List rangers, optional `active_only` |
| GET | `/patrols` | List patrols, optional `status` filter |
| GET | `/patrols/{id}` | Patrol detail with ordered waypoints |
| POST | `/patrols/generate` | **Optimizer-driven** patrol creation for a zone |
| PATCH | `/patrols/{id}/status` | Update patrol status |

`POST /patrols/generate` request body:
```json
{
  "zone_id": "ZON-xxxxxxxx",
  "scheduled_date": "2026-09-01T06:00:00",
  "team_size": 3,
  "lead_ranger_id": "RNG-xxxxxxxx",
  "max_waypoints": 6
}
```

## Veterinary

| Method | Path | Description |
|---|---|---|
| GET | `/vet-cases` | List cases, filters: `status`, `priority` |
| POST | `/vet-cases` | Report a new case (also flips the animal's status to `medical_care`) |
| PATCH | `/vet-cases/{id}/status` | Update case status, optionally assign a vet |

## CITES compliance

| Method | Path | Description |
|---|---|---|
| GET | `/cites-permits` | List permits |
| POST | `/cites-permits` | Create/issue a permit (auto-generates a permit number) |
| GET | `/cites-permits/{id}/pdf` | Download the generated permit PDF |

## Community engagement

| Method | Path | Description |
|---|---|---|
| GET | `/community-members` | List opted-in members, optional `zone_id` |
| GET | `/sms-alerts` | Broadcast history |
| POST | `/sms-alerts/broadcast` | Send an SMS broadcast to opted-in members (all, or filtered by zone) |

## Fundraising

| Method | Path | Description |
|---|---|---|
| GET | `/campaigns` | List campaigns, optional `active_only` |
| GET | `/donors` | List donors |
| GET | `/donations` | List donations, filters: `campaign_id`, `public_only` |
| POST | `/donations` | Record a donation (updates the linked campaign's raised total) |
| GET | `/fundraising/allocation-breakdown` | Sum of public donations grouped by program allocation |

## Dashboard

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | Aggregate KPIs for the operations overview screen |

## Error format

All errors return FastAPI's standard shape:
```json
{ "detail": "human-readable message" }
```
with an appropriate HTTP status code (404 for missing resources, 400/422 for validation errors).
