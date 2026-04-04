from fastapi import FastAPI, Request, status
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging
import uuid
import time

MAX_FILE_SIZE = 5 * 1024 * 1024 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        raise e

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

@app.get("/health")
def health_check(request: Request):
    return {
        "request_id": request.state.request_id,
        "status": "success",
        "data": {
            "service": "up"
        }
    }

@app.post("/contracts", status_code=202)
async def upload_contract(request: Request, file: UploadFile = File(...)):
    request_id = request.state.request_id

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail={
                "request_id": request_id,
                "status": "error",
                "error_code": "INVALID_FILE_TYPE",
                "message": "Only PDF files are allowed"
            }
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "request_id": request_id,
                "status": "error",
                "error_code": "FILE_TOO_LARGE",
                "message": "File exceeds size limit (5MB)"
            }
        )

    logger.info(f"request_id={request_id} received contract upload")

    return {
        "request_id": request_id,
        "status": "success",
        "data": {
            "message": "Contract received and queued for processing"
        }
    }

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