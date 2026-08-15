# Wildlife Guardian

**An IoT-enabled park management and anti-poaching platform for small and mid-sized wildlife conservancies.**

Wildlife Guardian brings GPS collar tracking, acoustic/thermal poacher detection, optimized ranger patrols, satellite habitat monitoring, veterinary case management, CITES trade documentation, drone surveillance, and donor transparency reporting into a single operational console — sized and priced for a conservancy running on a lean budget, not a national park with a seven-figure IT budget.

The repository ships with a realistic, fully-seeded demo dataset for a fictional East African conservancy so you can evaluate every feature immediately, with zero external accounts or paid APIs required.

> **Note on scope:** several integrations that require paid hardware or vendor accounts in the real world — satellite imagery feeds, SMS delivery, drone/camera-trap computer vision — are implemented here behind clean, documented interfaces with realistic simulated data and outputs. Swapping in a live data source (Sentinel Hub, Africa's Talking, a trained YOLO model, etc.) means implementing one function against a stable contract, not restructuring the platform. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for exactly where each seam is.

---

## Features

| Domain | What it does |
|---|---|
| **Species tracking** | GPS collar telemetry ingestion, live position map, per-animal movement history |
| **Movement prediction** | Predicts an animal's next likely location from water/forage availability in nearby habitat zones |
| **Threat detection** | Acoustic, thermal-camera, and seismic sensor network with alert triage workflow (new → acknowledged → dispatched → resolved) |
| **Drone surveillance** | Mission logging with computer-vision snare/human detection scoring |
| **Ranger patrols** | One-click optimized patrol route generation, prioritizing live alerts, offline sensors, and pending snare removals |
| **Habitat monitoring** | Satellite-derived vegetation (NDVI) and surface water indices per zone, on a biweekly cadence |
| **Veterinary logistics** | Case intake, priority triage, and status tracking tied back to animal records |
| **CITES compliance** | Structured permit records plus one-click PDF generation in standard CITES permit layout |
| **Community engagement** | SMS broadcast system (poaching warnings, wildlife proximity, community updates) to opted-in residents by zone |
| **Donor transparency** | Campaign progress bars, donation ledger, and spending-by-allocation breakdown |

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, SQLite by default (PostgreSQL-ready via `DATABASE_URL`)
- **Frontend:** Vanilla HTML/CSS/JS (no build step), Leaflet for mapping, Chart.js for charts
- **Docs generation:** interactive Swagger UI at `/docs`, auto-generated from the FastAPI schema

No framework lock-in, no bundler, no paid SaaS dependency to run the demo.

## Quick start

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Dashboard: http://localhost:8080

The database seeds itself automatically on first boot.

### Option B — Run locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed          # populate realistic sample data
uvicorn app.main:app --reload

# Frontend (separate terminal) — any static file server works
cd frontend
python -m http.server 8080
```

Open http://localhost:8080. The dashboard talks to the API at `http://localhost:8000/api/v1` by default (change `window.WILDLIFE_GUARDIAN_API_BASE` in `index.html` if you deploy the API elsewhere).

### Running tests

```bash
cd backend
pytest
```

## Project structure

```
wildlife-guardian/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + router wiring
│   │   ├── models.py          # SQLAlchemy ORM models (every domain)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── database.py        # Engine/session config
│   │   ├── seed.py            # Realistic sample data generator
│   │   ├── seed_if_empty.py   # Idempotent seed for container startup
│   │   ├── routers/           # One module per domain (tracking, security, patrols, ...)
│   │   └── services/          # Patrol optimizer, movement predictor, SMS gateway,
│   │                          # CV detection scorer, CITES PDF generator
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html             # Single-page operations console
│   ├── css/styles.css
│   └── js/{api.js,app.js}
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATA_MODEL.md
│   └── DEPLOYMENT.md
├── docker-compose.yml
├── .env.example
└── LICENSE
```

## Sample data

Every table is populated with internally-consistent, realistic demo data for a fictional **Northern Rift Conservancy** in Laikipia County, Kenya: 5 endangered/vulnerable species, 12 collared animals with two weeks of GPS history, 5 habitat zones with satellite-derived indices, 15 field sensors, 18 threat alerts, 9 drone missions, optimizer-generated ranger patrols, 10 rangers, veterinary cases, 4 CITES permits, 20 opted-in community members across 5 villages, and 12 donors with 35 donations across 3 active campaigns. All names, coordinates, and identifiers are synthetic.

To reset to a fresh dataset at any time: `python -m app.seed` (this drops and recreates all tables).

## License

MIT — see [`LICENSE`](LICENSE). Free to use, adapt, and deploy for your own conservancy.
