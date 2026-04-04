from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from db import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed
    created_at = Column(DateTime, default=datetime.utcnow)