"""
Seeds the database only if it has no species rows yet -- safe to run on
every container start without wiping data on restarts. For a full reset,
run `python -m app.seed` directly instead.
"""
from app.database import Base, engine, SessionLocal
from app import models
from app.seed import seed


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        has_data = db.query(models.Species).first() is not None
    finally:
        db.close()

    if has_data:
        print("Database already contains data; skipping seed.")
        return

    print("Database is empty; running seed...")
    seed()


if __name__ == "__main__":
    main()
