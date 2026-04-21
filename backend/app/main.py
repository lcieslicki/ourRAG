from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.routes.admin import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.chat_ws import router as chat_ws_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.documents import router as documents_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.config import get_settings
from app.infrastructure.llm import OllamaGatewayError, get_llm_gateway

settings = get_settings()

app = FastAPI(title="ourRAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.app.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(workspaces_router)
app.include_router(conversations_router)
app.include_router(chat_router)
app.include_router(chat_ws_router)
app.include_router(documents_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"env": settings.app.env, "status": "ok"}


@app.get("/ping", response_class=PlainTextResponse)
def ping() -> str:
    return "pong"


@app.get("/health/llm")
def llm_health() -> JSONResponse:
    gateway = get_llm_gateway(settings)
    try:
        is_ready, reason = gateway.readiness_check()
    except OllamaGatewayError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "provider": "ollama",
                "model": settings.ollama.model,
                "ready": False,
                "reason": str(exc),
            },
        )

    if not is_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "provider": "ollama",
                "model": settings.ollama.model,
                "ready": False,
                "reason": reason,
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "provider": "ollama",
            "model": settings.ollama.model,
            "ready": True,
            "reason": reason,
        },
    )
