"""
Wildlife Guardian - IoT-enabled park management & anti-poaching platform.

Entry point: wires up the database, CORS, and every domain router. Run with:
    uvicorn app.main:app --reload

Interactive API docs are auto-generated at /docs (Swagger UI) and /redoc.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.database import Base, engine
from app.routers import (
    tracking, security, patrols, veterinary, compliance, community, fundraising, dashboard,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.APP_NAME,
    description=(
        "IoT-enabled conservancy management platform: GPS collar tracking, "
        "acoustic/thermal poacher detection, optimized ranger patrols, "
        "SMS community alerts, satellite habitat monitoring, veterinary "
        "logistics, CITES documentation, drone surveillance, and donor "
        "transparency dashboards."
    ),
    version=config.API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracking.router)
app.include_router(security.router)
app.include_router(patrols.router)
app.include_router(veterinary.router)
app.include_router(compliance.router)
app.include_router(community.router)
app.include_router(fundraising.router)
app.include_router(dashboard.router)


@app.get("/", tags=["health"])
def root():
    return {
        "service": config.APP_NAME,
        "version": config.API_VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/api/v1/health", tags=["health"])
def health_check():
    return {"status": "ok"}
