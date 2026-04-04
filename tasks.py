from celery_app import celery_app
from db import SessionLocal
from models import Contract
import logging
import pdfplumber
import os
import re

logger = logging.getLogger(__name__)


# -------------------------------
# Text Cleaning
# -------------------------------
def clean_text(text: str) -> str:
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    return text


# -------------------------------
# Clause Extraction
# -------------------------------
def extract_clauses(text: str):
    clauses = []

    pattern = r"\n?\d+(?:\.\d+)*\s"

    splits = re.split(pattern, text)

    for chunk in splits:
        if not chunk:  # skip None / empty
            continue

        chunk = chunk.strip()

        if len(chunk) > 50:
            clauses.append(chunk)

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

        # 🔥 Optional but very useful (debugging)
        file_size = os.path.getsize(file_path)
        logger.info(
            f"file_found contract_id={contract_id} size={file_size} path={file_path}"
        )

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

        logger.info(
            f"pdf_extracted contract_id={contract_id} "
            f"total_chars={len(full_text)}"
        )

        # -------------------------------
        # Clean text
        # -------------------------------
        cleaned_text = clean_text(full_text)

        logger.info(
            f"text_cleaned contract_id={contract_id} "
            f"cleaned_chars={len(cleaned_text)}"
        )

        # -------------------------------
        # Extract clauses
        # -------------------------------
        clauses = extract_clauses(cleaned_text)

        logger.info(
            f"clauses_extracted contract_id={contract_id} "
            f"num_clauses={len(clauses)}"
        )

        # Preview first few clauses (debugging)
        for i, clause in enumerate(clauses[:2]):
            logger.info(
                f"clause_preview contract_id={contract_id} "
                f"index={i} length={len(clause)}"
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