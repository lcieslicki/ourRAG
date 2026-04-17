from dataclasses import dataclass, field
from typing import Protocol

from app.domain.prompting import PromptMessage


@dataclass(frozen=True)
class GenerationRequest:
    messages: tuple[PromptMessage, ...]
    model: str | None = None
    temperature: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResponse:
    text: str
    model: str
    provider: str
    finish_reason: str | None = None
    metadata: dict = field(default_factory=dict)


class LlmGateway(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        pass
