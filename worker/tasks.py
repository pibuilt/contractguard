from shared.celery_app import celery_app
from backend.db import SessionLocal
from backend.models import Contract, ClauseResult, ContractRisk
import logging
import os
import uuid
import numpy as np
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
# Clause Extraction
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

    from worker.services.llm_service import llm_service
    from worker.services.vector_instance import vector_store
    from worker.services.risk_detector import detect_risks
    from worker.services.embedding_instance import embedding_service
    from worker.services.explanation_service import generate_explanation

    db = SessionLocal()

    try:
        contract = db.get(Contract, contract_id)

        if not contract:
            logger.error(f"contract_not_found contract_id={contract_id}")
            return

        if contract.status == "processing":
            logger.warning(f"duplicate_task_detected contract_id={contract_id}")
            return

        contract.status = "processing"
        db.commit()

        logger.info(f"processing_started contract_id={contract_id}")

        # Cleanup old data
        db.query(ClauseResult).filter(
            ClauseResult.contract_id == contract_id
        ).delete(synchronize_session=False)

        db.query(ContractRisk).filter(
            ContractRisk.contract_id == contract_id
        ).delete(synchronize_session=False)

        db.commit()

        # File check
        if not os.path.exists(file_path):
            logger.error(f"file_not_found contract_id={contract_id}")
            contract.status = "failed"
            db.commit()
            return

        logger.info(
            f"file_found contract_id={contract_id} size={os.path.getsize(file_path)}"
        )

        # Extract text
        full_text = extract_text_from_pdf(file_path)

        logger.info(
            f"pdf_extracted contract_id={contract_id} total_chars={len(full_text)}"
        )

        # Extract clauses
        clauses = extract_clauses(full_text)

        if not clauses:
            paragraphs = [
                p.strip()
                for p in full_text.split("\n\n")
                if len(p.strip()) > 30
            ]

            clauses = [
                {"clause_number": None, "text": p}
                for p in paragraphs
            ]

        # Store clauses
        clause_objects = []

        for clause in clauses:
            obj = ClauseResult(
                contract_id=contract_id,
                clause_number=clause["clause_number"],
                text=clause["text"]
            )
            db.add(obj)
            clause_objects.append(obj)

        db.commit()

        # -------------------------------
        # 🔥 RISK DETECTION + ENRICHMENT
        # -------------------------------
        total_risks = 0

        for clause in clause_objects:
            risks = detect_risks(clause.text, llm_service=llm_service)

            if not risks:
                continue

            total_risks += len(risks)

            logger.info(
                f"risk_detected contract_id={contract_id} "
                f"clause_id={clause.id} risks={len(risks)}"
            )

            for risk in risks:

                if not all(k in risk for k in ["risk_type", "severity", "confidence"]):
                    continue

                # -------------------------------
                # 🔥 CONTROLLED LLM USAGE
                # -------------------------------
                llm_data = None
                should_call_llm = False

                # Reuse if already from LLM
                if risk.get("source") == "llm" and risk.get("llm_data"):
                    llm_data = risk["llm_data"]

                    logger.info(
                        f"llm_reused contract_id={contract_id} clause_id={clause.id}"
                    )

                # Only call LLM for HIGH severity
                elif risk.get("severity") == "high":
                    should_call_llm = True

                # Call LLM only if needed
                if should_call_llm:
                    try:
                        llm_data = llm_service.analyze_clause(clause.text)

                        logger.info(
                            f"llm_enrichment_called contract_id={contract_id} clause_id={clause.id}"
                        )

                    except Exception:
                        llm_data = None
                        logger.warning(
                            f"llm_enrichment_failed contract_id={contract_id}"
                        )

                # -------------------------------
                # Fallback (guaranteed safe)
                # -------------------------------
                if not llm_data:
                    explanation = generate_explanation(risk["risk_type"])
                else:
                    explanation = llm_data.get("why_risky", "") or generate_explanation(risk["risk_type"])

                # Store risk
                db.add(ContractRisk(
                    id=str(uuid.uuid4()),
                    contract_id=contract_id,
                    clause_id=clause.id,
                    risk_type=risk["risk_type"],
                    severity=risk["severity"],
                    confidence=risk["confidence"],
                    explanation=explanation
                ))

        db.commit()

        logger.info(
            f"risk_summary contract_id={contract_id} total_risks={total_risks}"
        )

        # -------------------------------
        # FAISS
        # -------------------------------
        try:
            texts = [c.text for c in clause_objects]

            if texts:
                embeddings = embedding_service.encode(texts)
                embeddings = np.array(embeddings).astype("float32")

                if len(embeddings.shape) == 1:
                    embeddings = embeddings.reshape(1, -1)

                ids = [str(c.id) for c in clause_objects]

                vector_store.add(embeddings, ids)
                vector_store.save("storage/faiss")

                logger.info(
                    f"faiss_index_updated contract_id={contract_id}"
                )

        except Exception as e:
            logger.error(
                f"faiss_index_failed contract_id={contract_id} error={str(e)}"
            )

        # Finalize
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