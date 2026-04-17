from collections.abc import Iterator

from app.domain.llm import LlmGateway
from app.infrastructure.llm import get_llm_gateway


def get_generation_gateway() -> Iterator[LlmGateway]:
    yield get_llm_gateway()
