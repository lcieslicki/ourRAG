from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.postgres.user,
    password=settings.postgres.password,
    host=settings.postgres.host,
    port=settings.postgres.port,
    database=settings.postgres.db,
)

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
