from celery_app import celery_app
from db import SessionLocal
from models import Contract, ClauseResult
import logging
import os

from pdfminer.high_level import extract_text

logger = logging.getLogger(__name__)


# -------------------------------
# Text Extraction (pdfminer)
# -------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    try:
        text = extract_text(file_path)
        return text or ""
    except Exception as e:
        logger.error(f"pdfminer_failed error={str(e)}")
        return ""


# -------------------------------
# Clause Extraction (structure-based)
# -------------------------------
def extract_clauses(text: str):
    clauses = []
    current = None

    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        words = line.split()
        first = words[0].rstrip(".")

        # detect clause start like 1 / 1.1 / 2.3.4
        if first.replace(".", "").isdigit() and len(first) < 10:
            if current:
                clauses.append(current)

            current = {
                "clause_number": first,
                "text": " ".join(words[1:])
            }
        else:
            if current:
                current["text"] += " " + line

    if current:
        clauses.append(current)

    return clauses


# -------------------------------
# Celery Task
# -------------------------------
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
        # File existence check
        # -------------------------------
        if not os.path.exists(file_path):
            logger.error(
                f"file_not_found contract_id={contract_id} path={file_path}"
            )

            contract.status = "failed"
            db.commit()
            return

        file_size = os.path.getsize(file_path)
        logger.info(
            f"file_found contract_id={contract_id} size={file_size} path={file_path}"
        )

        # -------------------------------
        # Extract text (pdfminer)
        # -------------------------------
        full_text = extract_text_from_pdf(file_path)

        logger.info(
            f"pdf_extracted contract_id={contract_id} "
            f"total_chars={len(full_text)}"
        )

        # -------------------------------
        # Extract clauses
        # -------------------------------
        clauses = extract_clauses(full_text)

        # Save clauses to DB
        for clause in clauses:
            clause_result = ClauseResult(
                contract_id=contract_id,
                clause_number=clause["clause_number"],
                clause_text=clause["text"]
            )
            db.add(clause_result)

        db.commit()

        logger.info(
            f"clauses_stored contract_id={contract_id} count={len(clauses)}"
        )

        # Preview first few clauses
        for i, clause in enumerate(clauses[:3]):
            logger.info(
                f"clause_preview contract_id={contract_id} "
                f"index={i} number={clause['clause_number']} "
                f"length={len(clause['text'])}"
            )

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

        try:
            contract.status = "failed"
            db.commit()
        except:
            pass

    finally:
        db.close()