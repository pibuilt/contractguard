from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import BLOB
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

class ContractRisk(Base):
    __tablename__ = "contract_risks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    clause_id = Column(String, ForeignKey("clause_results.id"), nullable=False)
    
    risk_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    
    explanation = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)