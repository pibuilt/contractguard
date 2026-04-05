from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base
import uuid


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed
    created_at = Column(DateTime, default=datetime.utcnow)

class ClauseResult(Base):
    __tablename__ = "clause_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    clause_number = Column(String, nullable=True)  # IMPORTANT
    text = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", backref="clauses")