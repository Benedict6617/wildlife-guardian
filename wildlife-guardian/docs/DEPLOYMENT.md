# Deployment Guide

## Local evaluation (fastest path)

```bash
cp .env.example .env
docker compose up --build
```

Visit http://localhost:8080 for the dashboard, http://localhost:8000/docs for the API.

## Small-conservancy production deployment

A realistic target for the platform this project describes: a single small VM (2 vCPU / 2–4 GB RAM is plenty), PostgreSQL for durability, and a static file host or the same VM serving the frontend behind Nginx.

### 1. Provision PostgreSQL

Any managed Postgres (a $15/month instance from a low-cost provider is sufficient at conservancy scale) or a self-hosted instance works. Create a database and user, then set:

```
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<dbname>
```

Add `psycopg2-binary` to `backend/requirements.txt` (it's the standard PostgreSQL driver for SQLAlchemy; omitted from the default requirements to keep the zero-config SQLite path dependency-free).

### 2. Run the backend

```bash
cd backend
pip install -r requirements.txt psycopg2-binary
python -m app.seed_if_empty   # safe to run on every deploy; only seeds an empty DB
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Put this behind a process manager (systemd, supervisord, or the provided Dockerfile) and a reverse proxy (Nginx/Caddy) that terminates TLS.

### 3. Serve the frontend

The frontend is fully static — upload the contents of `frontend/` to any static host (Nginx, S3+CloudFront, Netlify, GitHub Pages) or serve it from the same box via Nginx. Before deploying, set the API base URL in `frontend/index.html`:

```html
<script>
  window.WILDLIFE_GUARDIAN_API_BASE = "https://api.yourconservancy.org/api/v1";
</script>
```

### 4. CORS

Set `CORS_ORIGINS` in the backend environment to your deployed frontend's origin(s), comma-separated. Do not leave it as `*` in production.

### 5. SMS provider

Swap `SMS_PROVIDER` from `simulated` to a real provider once you've implemented the corresponding gateway class — see `docs/ARCHITECTURE.md` → "Where simulated integrations live". Africa's Talking is the most common choice for East African deployments (SMS + USSD, competitive per-message pricing, local carrier relationships); Twilio is a reasonable alternative for global reach.

### 6. Backups

If using SQLite (fine for a single-conservancy pilot), back up the `.db` file on a cron schedule. If using PostgreSQL, use your provider's automated backups or `pg_dump` on a schedule — donation and CITES permit records in particular should not be lost.

### 7. What to add before handling real donor payments or real CITES paperwork

- **Payments:** integrate a PCI-compliant processor (Stripe, Flutterwave, PayPal) for actual card/mobile-money collection. The `Donation` model here records an already-collected amount; it is not a payment form.
- **CITES:** the generated PDF is a documentation aid for your own records and pre-filling paperwork — actual permits must be issued through your country's CITES Management Authority. Do not represent the generated PDF as a valid legal permit on its own.
- **Auth:** add role-based authentication before exposing the API beyond a trusted internal network — see the "Security and multi-tenancy notes" section of `docs/ARCHITECTURE.md`.
