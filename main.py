from fastapi import FastAPI, Request, status, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging
import uuid
import time
import os

from db import engine, Base, SessionLocal
from models import Contract, ClauseResult, ContractRisk
from sqlalchemy.orm import Session

from services.embedding_service import EmbeddingService
from services.vector_instance import vector_store

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
embedding_service = EmbeddingService()
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
    vector_store.load("storage/faiss")
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

@app.get("/contracts/{contract_id}/analysis")
def get_contract_analysis(contract_id: int):
    db = SessionLocal()

    try:
        contract = db.get(Contract, contract_id)

        if not contract:
            raise HTTPException(status_code=404, detail="CONTRACT_NOT_FOUND")

        # If still processing
        if contract.status != "completed":
            return {
                "contract_id": contract_id,
                "status": contract.status,
                "risks": []
            }

        # Get risks
        risks = db.query(ContractRisk).filter(
            ContractRisk.contract_id == contract_id
        ).all()

        # Map clause_id → clause
        clause_map = {
            c.id: c for c in db.query(ClauseResult).filter(
                ClauseResult.contract_id == contract_id
            ).all()
        }

        response = []

        for risk in risks:
            clause = clause_map.get(risk.clause_id)

            if not clause:
                continue  # safety

            response.append({
                "clause_number": clause.clause_number,
                "text": clause.text,
                "risk_type": risk.risk_type,
                "explanation": risk.explanation,
                "confidence": risk.confidence
            })

        response.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "contract_id": contract_id,
            "status": "completed",
            "risks": response
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

@app.get("/search")
def search_clauses(
    request: Request,
    query: str,
    k: int = 5
):
    request_id = request.state.request_id
    start_time = time.time()

    db: Session = SessionLocal()

    try:
        # -------------------------------
        # Handle empty index before FAISS search
        # -------------------------------
        if len(vector_store.id_map) == 0:
            return {
                "request_id": request_id,
                "status": "success",
                "data": {
                    "query": query,
                    "results": []
                }
            }

        # -------------------------------
        # Encode query
        # -------------------------------
        t0 = time.time()
        query_embedding = embedding_service.encode([query])[0]
        embedding_time = time.time() - t0

        # -------------------------------
        # FAISS search
        # -------------------------------
        t1 = time.time()
        clause_ids = vector_store.search(query_embedding, k=k)
        faiss_time = time.time() - t1

        if not clause_ids:
            return {
                "request_id": request_id,
                "status": "success",
                "data": {
                    "query": query,
                    "results": []
                }
            }

        # -------------------------------
        # Fetch from DB
        # -------------------------------
        clauses = db.query(ClauseResult).filter(
            ClauseResult.id.in_(clause_ids)
        ).all()

        # -------------------------------
        # 🔥 PRESERVE FAISS ORDER (IMPORTANT FIX)
        # -------------------------------
        clause_map = {c.id: c for c in clauses}

        ordered_results = []
        for cid in clause_ids:
            c = clause_map.get(cid)
            if c:
                ordered_results.append({
                    "clause_id": c.id,
                    "contract_id": c.contract_id,
                    "clause_number": c.clause_number,
                    "text": c.text
                })

        total_time = time.time() - start_time

        # -------------------------------
        # Logging
        # -------------------------------
        logger.info(
            f"request_id={request_id} "
            f"search_query='{query}' "
            f"results={len(ordered_results)} "
            f"embedding_time={embedding_time:.4f}s "
            f"faiss_time={faiss_time:.4f}s "
            f"total_time={total_time:.4f}s"
        )

        return {
            "request_id": request_id,
            "status": "success",
            "data": {
                "query": query,
                "results": ordered_results
            }
        }

    finally:
        db.close()
        
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