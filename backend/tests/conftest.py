from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.db.session import SessionLocal


@pytest.fixture()
def db_session() -> Iterator[Session]:
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
