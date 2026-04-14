import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------
# Dynamic DB path (LOCAL vs DOCKER)
# ---------------------------------
BASE_DIR = os.getcwd()

DB_PATH = os.path.join(BASE_DIR, "storage", "db")
os.makedirs(DB_PATH, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(DB_PATH, 'contracts.db')}"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()