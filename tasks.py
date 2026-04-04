from celery_app import celery_app
from db import SessionLocal
from models import Contract
import time
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def process_contract(contract_id: int):
    db = SessionLocal()

    try:
        contract = db.query(Contract).get(contract_id)

        if not contract:
            logger.error(f"Contract {contract_id} not found")
            return

        contract.status = "processing"
        db.commit()

        logger.info(f"Processing contract_id={contract_id}")

        time.sleep(5)

        contract.status = "completed"
        db.commit()

        logger.info(f"Finished processing contract_id={contract_id}")

    finally:
        db.close()