from fastapi import FastAPI
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
def health_check():
    logger.info("Health check endpoint hit")
    return {"status": "ok"}