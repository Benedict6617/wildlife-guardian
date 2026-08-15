FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Seed on first boot only if the database file doesn't exist yet, then serve.
# DATABASE_URL may point at ./wildlife_guardian.db (local/dev) or a mounted
# volume path such as /app/data/wildlife_guardian.db (docker-compose).
RUN mkdir -p /app/data
CMD ["sh", "-c", "python -m app.seed_if_empty; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
