import threading
import time

import httpx
import pytest

from app.domain.llm import GenerationRequest
from app.domain.prompting import PromptMessage
from app.infrastructure.llm.ollama import OllamaGateway, OllamaGatewayError, parse_ollama_chat_response


def test_ollama_gateway_sends_non_streaming_chat_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "bielik",
                "message": {"role": "assistant", "content": "Odpowiedz z dokumentow."},
                "done": True,
                "done_reason": "stop",
                "eval_count": 12,
            },
        )

    gateway = gateway_with_client(httpx.Client(transport=httpx.MockTransport(handler)))

    response = gateway.generate(
        GenerationRequest(
            messages=(
                PromptMessage(role="system", content="Use context only."),
                PromptMessage(role="user", content="Jak poprosic o urlop?"),
            ),
            temperature=0.2,
        )
    )

    assert response.text == "Odpowiedz z dokumentow."
    assert response.model == "bielik"
    assert response.provider == "ollama"
    assert response.finish_reason == "stop"
    assert response.metadata["eval_count"] == 12
    assert requests[0].url == "http://ollama:11434/api/chat"
    assert requests[0].read() == (
        b'{"model":"bielik","messages":[{"role":"system","content":"Use context only."},'
        b'{"role":"user","content":"Jak poprosic o urlop?"}],"stream":false,'
        b'"keep_alive":"5m","options":{"temperature":0.2}}'
    )


def test_ollama_gateway_allows_request_model_override() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"model": "custom", "message": {"content": "ok"}, "done": True})

    gateway = gateway_with_client(httpx.Client(transport=httpx.MockTransport(handler)))

    gateway.generate(
        GenerationRequest(
            model="custom",
            messages=(PromptMessage(role="user", content="Hi"),),
        )
    )

    assert b'"model":"custom"' in requests[0].read()


def test_ollama_gateway_retries_timeout_once() -> None:
    calls = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.TimeoutException("timed out")
        return httpx.Response(200, json={"model": "bielik", "message": {"content": "ok"}, "done": True})

    gateway = gateway_with_client(
        httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=1,
        retry_backoff_seconds=0,
    )

    response = gateway.generate(GenerationRequest(messages=(PromptMessage(role="user", content="Hi"),)))

    assert response.text == "ok"
    assert calls["count"] == 2


def test_ollama_gateway_raises_after_retry_exhaustion() -> None:
    gateway = gateway_with_client(
        httpx.Client(transport=httpx.MockTransport(lambda _: (_ for _ in ()).throw(httpx.TimeoutException("slow")))),
        max_retries=1,
        retry_backoff_seconds=0,
    )

    with pytest.raises(OllamaGatewayError):
        gateway.generate(GenerationRequest(messages=(PromptMessage(role="user", content="Hi"),)))


def test_ollama_gateway_raises_on_http_error_without_retrying_bad_request() -> None:
    calls = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(400, json={"error": "bad request"})

    gateway = gateway_with_client(httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(OllamaGatewayError):
        gateway.generate(GenerationRequest(messages=(PromptMessage(role="user", content="Hi"),)))

    assert calls["count"] == 1


def test_ollama_gateway_limits_concurrent_requests() -> None:
    active = 0
    max_active = 0
    lock = threading.Lock()

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return httpx.Response(200, json={"model": "bielik", "message": {"content": "ok"}, "done": True})

    gateway = gateway_with_client(
        httpx.Client(transport=httpx.MockTransport(handler)),
        max_concurrency=1,
    )
    threads = [
        threading.Thread(
            target=lambda: gateway.generate(GenerationRequest(messages=(PromptMessage(role="user", content="Hi"),)))
        )
        for _ in range(3)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max_active == 1


def test_ollama_gateway_rejects_empty_messages() -> None:
    gateway = gateway_with_client(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))))

    with pytest.raises(ValueError):
        gateway.generate(GenerationRequest(messages=()))


def test_parse_ollama_chat_response_rejects_missing_content() -> None:
    with pytest.raises(OllamaGatewayError):
        parse_ollama_chat_response({"model": "bielik", "message": {"role": "assistant"}})


def gateway_with_client(
    client: httpx.Client,
    *,
    max_retries: int = 1,
    retry_backoff_seconds: float = 0,
    max_concurrency: int = 2,
) -> OllamaGateway:
    return OllamaGateway(
        base_url="http://ollama:11434",
        model="bielik",
        timeout_seconds=60,
        keep_alive="5m",
        max_concurrency=max_concurrency,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        client=client,
    )
