# -------- BUILD STAGE --------
FROM python:3.10-slim AS builder

WORKDIR /app

# Install torch first (heavy dep)
RUN pip install --no-cache-dir \
https://download.pytorch.org/whl/cpu/torch-2.2.2%2Bcpu-cp310-cp310-linux_x86_64.whl

# Copy requirements
COPY requirements.worker.txt .

# Install ALL deps directly into system site-packages
RUN pip install --no-cache-dir -r requirements.worker.txt


# -------- RUNTIME STAGE --------
FROM python:3.10-slim

WORKDIR /app

# Copy full Python environment (correct path)
COPY --from=builder /usr/local /usr/local

# Copy code
COPY worker/ worker/
COPY backend/ backend/
COPY shared/ shared/

# Run worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=1", "--prefetch-multiplier=1"]