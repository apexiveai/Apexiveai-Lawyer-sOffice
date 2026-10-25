from pathlib import Path

from alembic import command
from alembic.config import Config
from app.db.database import DATABASE_URL

def init_db():
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        DATABASE_URL.replace("%", "%%"),
    )
    command.upgrade(config, "head")

if __name__ == "__main__":

    init_db()