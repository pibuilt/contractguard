# -------- BUILD STAGE --------
FROM python:3.10-slim AS builder

WORKDIR /install

COPY requirements.worker.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.worker.txt


# -------- RUNTIME STAGE --------
FROM python:3.10-slim

WORKDIR /app

# Copy installed deps
COPY --from=builder /install /usr/local

# Copy code
COPY worker/ worker/
COPY backend/ backend/

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--pool=solo"]