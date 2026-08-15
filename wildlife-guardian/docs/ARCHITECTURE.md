# Architecture

## Overview

Wildlife Guardian is a conventional three-tier web application: a static frontend, a stateless REST API, and a relational database. This document explains the major design decisions and — most importantly for anyone extending this into a production deployment — exactly where each simulated integration lives and what its real-world replacement looks like.

```
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────┐
│   Frontend       │  HTTP  │   FastAPI backend     │  ORM   │  Database    │
│  (static HTML/   │───────▶│   app/main.py         │───────▶│  SQLite/     │
│   JS, Leaflet,   │◀───────│   app/routers/*       │◀───────│  PostgreSQL  │
│   Chart.js)      │  JSON  │   app/services/*      │        │              │
└─────────────────┘        └──────────────────────┘        └─────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                   ▼
            IoT collar feed      Sensor network      Satellite imagery
            (device → API)     (acoustic/thermal)    (Sentinel-2 etc.)
```

## Why these choices

**FastAPI + SQLAlchemy over a bigger framework.** A conservancy-scale deployment (dozens of sensors, low hundreds of animals, single-digit ranger teams) does not need a distributed microservice architecture. A single well-organized monolith is easier for a small IT team or an outside contractor to operate, debug, and extend. Routers are still split by domain (`tracking`, `security`, `patrols`, `veterinary`, `compliance`, `community`, `fundraising`, `dashboard`) so the codebase reads like a set of bounded contexts even though it deploys as one process.

**SQLite by default, PostgreSQL via one environment variable.** Zero-config evaluation matters for a nonprofit deciding whether to adopt this platform. `DATABASE_URL` is the only thing that changes to move to PostgreSQL for real concurrent field use (see `app/database.py`).

**No frontend build step.** Field IT support in rural conservancies is often a single person. A static HTML/CSS/JS bundle that runs from any web server (or literally `file://` with CORS relaxed) is far easier to keep running for years than a framework with an npm dependency tree that goes stale.

**Explainable algorithms over black-box ML where a black box isn't justified.** The patrol route optimizer and movement predictor are both deterministic, documented heuristics rather than trained models. Rangers need to trust and be able to override a recommended route; "the model said so" is not an acceptable answer in the field. Both services document their scoring logic inline and are designed to be replaced by trained models later, once enough historical data (multi-season GPS tracks, patrol outcomes) exists to train on.

## Where simulated integrations live, and how to go live

This project intentionally ships with **simulated implementations behind real interfaces** for the pieces of the prompt that require hardware, vendor accounts, or trained models that don't exist yet. Every one of them is isolated to a single file so a real implementation is a drop-in replacement.

| Capability | File | Simulated behavior | To go live |
|---|---|---|---|
| SMS delivery | `app/services/sms_gateway.py` | Logs the message and reports 100% delivery | Implement `AfricasTalkingGateway`/`TwilioGateway` subclasses of `SMSGateway`, register in `get_gateway()`, set `SMS_PROVIDER` env var |
| Satellite imagery | `models.SatelliteImage` records, generated in `app/seed.py` | NDVI/water-index values computed as plausible synthetic numbers per zone | Replace the seed step with a scheduled job that pulls Sentinel-2/Planet imagery for each zone's bounding box and computes real NDVI |
| Snare/human CV detection | `app/services/vision_detection.py` | `score_frame()` takes lightweight scene features and returns a rule-based simulated verdict | Replace the function body with an inference call to a trained YOLO-family detector (ONNX Runtime, Triton, or a hosted vision API); keep the same `{kind, confidence_pct, notes}` return contract |
| CITES permit issuance | `app/services/cites_pdf.py` | Generates a correctly-laid-out PDF, explicitly marked "not valid without Management Authority signature" | This is a documentation aid, not a government system — real permits must be issued by a national CITES Management Authority. The generated PDF is meant to accompany that process (drafting, record-keeping), not replace it |
| GPS collar ingestion | `models.GPSPing`, seeded directly | Historical pings generated via a bounded random walk around each animal's home zone | Add an ingestion endpoint (or a message-queue consumer) that accepts pings from your collar vendor's webhook/API and inserts `GPSPing` rows the same way `app/seed.py` does |

## Patrol optimization algorithm

See the module docstring in `app/services/patrol_optimizer.py` for the full explanation. In short: candidate waypoints are drawn from unresolved alerts, unhealthy sensors, and pending snare removals inside a zone, scored by severity and recency, and then sequenced with a nearest-neighbor walk starting from the zone's ranger station. This is intentionally a fast, explainable heuristic rather than a full vehicle-routing solve — appropriate for the waypoint counts (single digits to low tens) a conservancy patrol actually has. If patrol areas grow large enough that tour quality starts to matter more than the sub-second response time, swap the sequencing step for an OR-Tools VRP solve; the candidate-scoring step does not need to change.

## Movement prediction algorithm

See `app/services/movement_predictor.py`. The model scores nearby habitat zones by a weighted combination of water index, forage index, and travel cost from the animal's last known position, then projects a point toward the highest-scoring zone, capped by a species-appropriate max daily displacement. This mirrors the actual ecological driver of large-herbivore movement (resource availability) without requiring a trained trajectory model — useful from day one, and straightforward to replace with an LSTM/transformer trajectory model once multiple seasons of per-animal GPS history have accumulated.

## Security and multi-tenancy notes

This reference implementation does not include authentication/authorization, rate limiting, or audit logging — deliberately, to keep the codebase readable as a foundation. Before any real deployment:

- Put the API behind authentication (e.g. OAuth2/JWT via FastAPI's built-in security utilities) and scope roles (ranger, vet, admin, donor-viewer) to the relevant routers.
- Add audit logging on alert status changes, permit issuance, and donation records — all of these have compliance/trust implications.
- If donor payment collection is added, integrate a PCI-compliant processor (Stripe, Flutterwave) rather than storing card data — the current `Donation` model only stores an already-collected amount, never payment instrument details.
