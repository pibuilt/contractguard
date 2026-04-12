# -------- BUILD STAGE --------
FROM python:3.10-slim AS builder

WORKDIR /install

COPY requirements.backend.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.backend.txt


# -------- RUNTIME STAGE --------
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONPATH=/app
# Copy installed deps from builder
COPY --from=builder /install /usr/local

# Copy only backend code
COPY backend/ backend/
COPY shared/ shared/

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]