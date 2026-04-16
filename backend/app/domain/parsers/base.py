from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ParsedBlock:
    kind: str
    text: str
    section_path: tuple[str, ...]
    heading: str | None = None
    level: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    normalized_text: str
    blocks: tuple[ParsedBlock, ...]
    parser_name: str
    parser_version: str


class Parser(Protocol):
    supported_extensions: tuple[str, ...]

    def parse(self, content: bytes) -> ParsedDocument:
        pass


class ParserRegistry:
    def __init__(self, parsers: list[Parser] | None = None) -> None:
        self._parsers_by_extension: dict[str, Parser] = {}

        for parser in parsers or []:
            self.register(parser)

    def register(self, parser: Parser) -> None:
        for extension in parser.supported_extensions:
            self._parsers_by_extension[normalize_extension(extension)] = parser

    def get(self, file_extension: str) -> Parser:
        extension = normalize_extension(file_extension)

        try:
            return self._parsers_by_extension[extension]
        except KeyError as exc:
            raise ValueError(f"No parser registered for extension: {extension}") from exc


def normalize_extension(extension: str) -> str:
    cleaned = extension.lower().strip()
    return cleaned if cleaned.startswith(".") else f".{cleaned}"
