from celery_app import celery_app
from db import SessionLocal
from models import Contract
import logging
import pdfplumber
import os

logger = logging.getLogger(__name__)


@celery_app.task
def process_contract(contract_id: int, file_path: str):
    db = SessionLocal()

    try:
        contract = db.query(Contract).get(contract_id)

        if not contract:
            logger.error(f"contract_not_found contract_id={contract_id}")
            return

        # -------------------------------
        # Mark as processing
        # -------------------------------
        contract.status = "processing"
        db.commit()

        logger.info(f"processing_started contract_id={contract_id}")

        # -------------------------------
        # File existence check (ADD HERE)
        # -------------------------------
        if not os.path.exists(file_path):
            logger.error(
                f"file_not_found contract_id={contract_id} path={file_path}"
            )

            contract.status = "failed"
            db.commit()
            return

        # -------------------------------
        # Extract text from PDF
        # -------------------------------
        full_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""

                logger.info(
                    f"page_extracted contract_id={contract_id} "
                    f"page={page_num} chars={len(text)}"
                )

                full_text += text + "\n"

        # -------------------------------
        # Log extraction result
        # -------------------------------
        logger.info(
            f"pdf_extracted contract_id={contract_id} "
            f"total_chars={len(full_text)}"
        )

        # -------------------------------
        # TEMP: no DB storage yet
        # -------------------------------

        # -------------------------------
        # Mark as completed
        # -------------------------------
        contract.status = "completed"
        db.commit()

        logger.info(f"processing_completed contract_id={contract_id}")

    except Exception as e:
        logger.error(
            f"processing_failed contract_id={contract_id} error={str(e)}",
            exc_info=True
        )

        # -------------------------------
        # Mark as failed
        # -------------------------------
        try:
            contract.status = "failed"
            db.commit()
        except:
            pass

    finally:
        db.close()