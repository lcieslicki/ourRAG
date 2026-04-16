from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="ourRAG API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"env": settings.app.env, "status": "ok"}
