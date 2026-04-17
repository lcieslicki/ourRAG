from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.documents import router as documents_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="ourRAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(workspaces_router)
app.include_router(conversations_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"env": settings.app.env, "status": "ok"}
