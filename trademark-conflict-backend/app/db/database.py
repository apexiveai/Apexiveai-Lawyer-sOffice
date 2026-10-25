from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, make_url
from sqlalchemy.engine import URL

from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

if os.getenv("DB_HOST"):
    DATABASE_URL = URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "trademark"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "trademark_conflict"),
    ).render_as_string(hide_password=False)
elif os.getenv("DATABASE_URL"):
    DATABASE_URL = os.environ["DATABASE_URL"]
else:
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'trademark_conflict.db'}"

class Base(DeclarativeBase):

    pass

engine_options = {"pool_pre_ping": True}
if make_url(DATABASE_URL).get_backend_name() == "sqlite":
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(

    bind=engine,

    autoflush=False,

    autocommit=False,

)

def get_db():

    db: Session = SessionLocal()

    try:

        yield db

    finally:

        db.close()