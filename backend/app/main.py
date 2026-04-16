from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="ourRAG API")
app.include_router(documents_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"env": settings.app.env, "status": "ok"}
