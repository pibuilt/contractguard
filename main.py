from fastapi import FastAPI, Request, status, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging
import uuid
import time
import os

from db import engine, Base, SessionLocal
from models import Contract, ClauseResult
from sqlalchemy.orm import Session

from tasks import process_contract

# -------------------------------
# Config
# -------------------------------
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
STORAGE_DIR = "storage/contracts"
os.makedirs(STORAGE_DIR, exist_ok=True)

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    force=True
)

logger = logging.getLogger(__name__)

# -------------------------------
# App Init
# -------------------------------
app = FastAPI()

# -------------------------------
# Middleware
# -------------------------------
@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception:
        raise

    process_time = time.time() - start_time

    logger.info(
        f"request_id={request_id} "
        f"method={request.method} "
        f"path={request.url.path} "
        f"status_code={response.status_code} "
        f"latency={process_time:.4f}s"
    )

    response.headers["X-Request-ID"] = request_id
    return response


# -------------------------------
# Startup (DB Init)
# -------------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


# -------------------------------
# Health Endpoint
# -------------------------------
@app.get("/health")
def health_check(request: Request):
    return {
        "request_id": request.state.request_id,
        "status": "success",
        "data": {
            "service": "up"
        }
    }


# -------------------------------
# Upload Contract Endpoint
# -------------------------------
@app.post("/contracts", status_code=202)
async def upload_contract(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id

    # -------------------------------
    # Validate file type
    # -------------------------------
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_FILE_TYPE",
                "message": "Only PDF files are allowed"
            }
        )

    # -------------------------------
    # Read file
    # -------------------------------
    content = await file.read()

    # -------------------------------
    # Validate size
    # -------------------------------
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": "File exceeds size limit (5MB)"
            }
        )

    logger.info(f"request_id={request_id} received contract upload")

    # -------------------------------
    # Save file to disk
    # -------------------------------
    file_id = str(uuid.uuid4())
    file_path = os.path.join(STORAGE_DIR, f"{file_id}.pdf")
    file_path = os.path.normpath(file_path)

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"request_id={request_id} file_saved path={file_path}")

    # -------------------------------
    # Save to DB
    # -------------------------------
    db: Session = SessionLocal()

    try:
        contract = Contract(
            filename=file.filename,
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
    finally:
        db.close()

    logger.info(f"request_id={request_id} stored contract_id={contract.id}")

    # -------------------------------
    # Enqueue background task   
    # -------------------------------
    process_contract.delay(contract.id, file_path)

    # -------------------------------
    # Response
    # -------------------------------
    return {
        "request_id": request_id,
        "status": "success",
        "data": {
            "contract_id": contract.id,
            "message": "Contract received and queued for processing"
        }
    }

# -------------------------------
# Get Contract Clauses Endpoint
# -------------------------------
@app.get("/contracts/{contract_id}/clauses")
def get_clauses(contract_id: int, request: Request):
    request_id = request.state.request_id
    db: Session = SessionLocal()

    try:
        # -------------------------------
        # Check contract exists
        # -------------------------------
        contract = db.get(Contract, contract_id)

        if not contract:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "CONTRACT_NOT_FOUND",
                    "message": "Contract does not exist"
                }
            )

        # -------------------------------
        # Fetch clauses
        # -------------------------------
        clauses = db.query(ClauseResult).filter(
            ClauseResult.contract_id == contract_id
        ).all()

        # -------------------------------
        # Return response (NO 404 for empty)
        # -------------------------------
        return {
            "request_id": request_id,
            "status": "success",
            "data": {
                "contract_id": contract_id,
                "status": contract.status,
                "clauses": [
                    {
                        "clause_number": c.clause_number,
                        "text": c.text
                    }
                    for c in clauses
                ]
            }
        }

    finally:
        db.close()

# -------------------------------
# HTTP Exception Handler
# -------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")

    detail = exc.detail if isinstance(exc.detail, dict) else {}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "request_id": request_id,
            "status": "error",
            "error_code": detail.get("error_code", "HTTP_ERROR"),
            "message": detail.get("message", str(exc.detail))
        }
    )


# -------------------------------
# Global Exception Handler
# -------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"request_id={request_id} error={str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "request_id": request_id,
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Something went wrong"
        }
    )