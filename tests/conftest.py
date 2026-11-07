import os
import tempfile
from pathlib import Path

# Must run before anything imports src.api.models, which builds the engine
# from settings at import time. Keeps tests away from the real jobs.db.
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="modgent-tests-")) / "test.db")

import pytest  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from src.api.models import engine, init_db  # noqa: E402


@pytest.fixture
def session():
    SQLModel.metadata.drop_all(engine)
    init_db()
    with Session(engine) as db:
        yield db
