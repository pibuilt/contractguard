from celery_app import celery_app
from db import SessionLocal
from models import Contract, ClauseResult, ContractRisk
import logging
import os
import uuid

from services.vector_instance import vector_store
from services.risk_detector import detect_risks
from services.embedding_instance import embedding_service
from services.explanation_service import generate_explanation

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

        is_clause_number = (
            first.replace(".", "").isdigit()
            and first.count(".") <= 3
            and len(first) <= 6
        )

        if is_clause_number:
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
        contract = db.get(Contract, contract_id)

        if not contract:
            logger.error(f"contract_not_found contract_id={contract_id}")
            return

        # 🚨 Idempotency guard
        if contract.status == "processing":
            logger.warning(f"duplicate_task_detected contract_id={contract_id}")
            return

        # -------------------------------
        # Mark as processing
        # -------------------------------
        contract.status = "processing"
        db.commit()

        logger.info(f"processing_started contract_id={contract_id}")

        # -------------------------------
        # Cleanup old clauses (idempotent)
        # -------------------------------
        db.query(ClauseResult).filter(
            ClauseResult.contract_id == contract_id
        ).delete(synchronize_session=False)
        db.commit()
        # -------------------------------
        # Cleanup old risks (idempotent)
        # -------------------------------
        db.query(ContractRisk).filter(
            ContractRisk.contract_id == contract_id
        ).delete(synchronize_session=False)
        db.commit()

        # -------------------------------
        # File check
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
            f"file_found contract_id={contract_id} size={file_size}"
        )

        # -------------------------------
        # Extract text
        # -------------------------------
        full_text = extract_text_from_pdf(file_path)

        logger.info(
            f"pdf_extracted contract_id={contract_id} total_chars={len(full_text)}"
        )

        # -------------------------------
        # Extract clauses
        # -------------------------------
        clauses = extract_clauses(full_text)

        # Fallback
        if not clauses:
            logger.warning(
                f"no_structured_clauses contract_id={contract_id}, using fallback"
            )

            paragraphs = [
                p.strip()
                for p in full_text.split("\n\n")
                if len(p.strip()) > 30
            ]

            clauses = [
                {"clause_number": None, "text": p}
                for p in paragraphs
            ]

        # -------------------------------
        # Store clauses (IMPORTANT FIX)
        # -------------------------------
        clause_objects = []

        for clause in clauses:
            obj = ClauseResult(
                contract_id=contract_id,
                clause_number=clause["clause_number"],
                text=clause["text"]
            )
            db.add(obj)
            clause_objects.append(obj)

        db.commit()  # IDs now available

        # -------------------------------
        # 🔥 RISK DETECTION (NEW)
        # -------------------------------
        try:
            total_risks = 0

            for clause in clause_objects:
                risks = detect_risks(clause.text)

                if risks:
                    total_risks += len(risks)

                    logger.info(
                        f"risk_detected contract_id={contract_id} "
                        f"clause_id={clause.id} risks={len(risks)} "
                        f"types={[r['risk_type'] for r in risks]}"
                    )

                    # ✅ NEW: Persist risks
                    for risk in risks:
                        if not all(k in risk for k in ["risk_type", "severity", "confidence"]):
                            logger.warning(
                                    f"invalid_risk_format contract_id={contract_id} clause_id={clause.id} risk={risk}"
                            )
                            continue

                        db.add(ContractRisk(
                            id=str(uuid.uuid4()),
                            contract_id=contract_id,
                            clause_id=clause.id,
                            risk_type=risk["risk_type"],
                            severity=risk["severity"],
                            confidence=risk["confidence"],
                            explanation=generate_explanation(risk["risk_type"])
                        ))

            # ✅ IMPORTANT: commit ONCE after loop
            db.commit()

            logger.info(
                f"risk_summary contract_id={contract_id} total_risks={total_risks}"
            )

        except Exception as e:

            db.rollback()  

            logger.error(
                f"risk_detection_failed contract_id={contract_id} error={str(e)}",
                exc_info=True
            )
        # -------------------------------
        # 🔥 FAISS INTEGRATION
        # -------------------------------
        try:
            texts = [c.text for c in clause_objects]
            ids = [c.id for c in clause_objects]

            if texts:
                embeddings = embedding_service.encode(texts)

                vector_store.add(embeddings, ids)
                vector_store.save("storage/faiss")

                logger.info(
                    f"faiss_index_updated contract_id={contract_id} vectors_added={len(ids)}"
                )

        except Exception as e:
            logger.error(
                f"faiss_index_failed contract_id={contract_id} error={str(e)}",
                exc_info=True
            )

        # -------------------------------
        # Preview logs
        # -------------------------------
        for i, clause in enumerate(clause_objects[:3]):
            logger.info(
                f"clause_preview contract_id={contract_id} "
                f"index={i} number={clause.clause_number} "
                f"length={len(clause.text)}"
            )

        # -------------------------------
        # Mark completed
        # -------------------------------
        contract.status = "completed"
        db.commit()

        logger.info(f"processing_completed contract_id={contract_id}")

    except Exception as e:
        db.rollback()

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