from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.infrastructure.db.session import engine

pytest.FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session: Session, transaction) -> None:
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
