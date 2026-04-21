from collections.abc import Callable
from threading import BoundedSemaphore
import time

import httpx

from app.core.config import Settings, get_settings
from app.domain.llm import GenerationRequest, GenerationResponse
from app.domain.prompting import PromptMessage


class OllamaGatewayError(RuntimeError):
    pass


class OllamaGateway:
    provider = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int,
        keep_alive: str,
        max_concurrency: int,
        max_retries: int = 1,
        retry_backoff_seconds: float = 0.1,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None
        self._semaphore = BoundedSemaphore(max_concurrency)

    @classmethod
    def from_settings(cls, settings: Settings, *, client: httpx.Client | None = None) -> "OllamaGateway":
        return cls(
            base_url=f"http://{settings.ollama.host}:{settings.ollama.port}",
            model=settings.ollama.model,
            timeout_seconds=settings.ollama.timeout_seconds,
            keep_alive=settings.ollama.keep_alive,
            max_concurrency=settings.ollama.max_concurrency,
            client=client,
        )

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not request.messages:
            raise ValueError("Generation request must include at least one message.")

        payload = {
            "model": request.model or self.model,
            "messages": [serialize_message(message) for message in request.messages],
            "stream": False,
            "keep_alive": self.keep_alive,
        }
        if request.temperature is not None:
            payload["options"] = {"temperature": request.temperature}
        debug_hook = request.metadata.get("debug_hook")
        if callable(debug_hook):
            cast_hook = debug_hook
            cast_hook(
                "llm.started",
                {
                    "provider": self.provider,
                    "model": payload["model"],
                    "messages": payload["messages"],
                    "options": payload.get("options"),
                },
            )
        else:
            cast_hook = None

        with self._semaphore:
            response = self._send_with_retries(payload)
        if cast_hook:
            cast_hook(
                "llm.completed",
                {
                    "provider": response.provider,
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                    "metadata": response.metadata,
                    "text_preview": response.text[:5000],
                },
            )
        return response

    def _send_with_retries(self, payload: dict) -> GenerationResponse:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._send(payload)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_backoff_seconds * (attempt + 1))

        raise OllamaGatewayError(f"Ollama generation request failed: {last_error}") from last_error

    def _send(self, payload: dict) -> GenerationResponse:
        try:
            response = self._client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise
        except httpx.HTTPStatusError as exc:
            raise OllamaGatewayError(f"Ollama generation request failed with status {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise OllamaGatewayError(f"Ollama generation request failed: {exc}") from exc

        return parse_ollama_chat_response(response.json())

    def readiness_check(self) -> tuple[bool, str]:
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
            models = payload.get("models")
            if not isinstance(models, list):
                raise OllamaGatewayError("Ollama tags response did not include a models list.")

            configured_model = self.model
            available_names = {
                str(model.get("name") or "").strip()
                for model in models
                if isinstance(model, dict)
            }
            if configured_model in available_names:
                return True, "ready"

            if any(name.startswith(f"{configured_model}:") for name in available_names):
                return True, "ready"

            return False, "model_missing"
        except httpx.TimeoutException as exc:
            raise OllamaGatewayError("Ollama readiness check timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaGatewayError(
                f"Ollama readiness check failed with status {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaGatewayError(f"Ollama readiness check failed: {exc}") from exc


def serialize_message(message: PromptMessage) -> dict:
    return {
        "role": message.role,
        "content": message.content,
    }


def parse_ollama_chat_response(payload: dict) -> GenerationResponse:
    message = payload.get("message")
    if not isinstance(message, dict):
        raise OllamaGatewayError("Ollama response did not include a message object.")

    content = message.get("content")
    if not isinstance(content, str):
        raise OllamaGatewayError("Ollama response message did not include string content.")

    return GenerationResponse(
        text=content,
        model=str(payload.get("model") or ""),
        provider=OllamaGateway.provider,
        finish_reason=str(payload["done_reason"]) if "done_reason" in payload else None,
        metadata={
            "done": payload.get("done"),
            "total_duration": payload.get("total_duration"),
            "load_duration": payload.get("load_duration"),
            "prompt_eval_count": payload.get("prompt_eval_count"),
            "eval_count": payload.get("eval_count"),
        },
    )


def get_llm_gateway(settings: Settings | None = None) -> OllamaGateway:
    return OllamaGateway.from_settings(settings or get_settings())
