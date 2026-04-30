from dataclasses import dataclass


@dataclass(frozen=True)
class ParseFailure:
    """
    Represents a failure to parse a document.
    Used when parsing encounters unrecoverable errors.
    """

    filename: str
    reason: str  # "encrypted", "empty", "corrupt", "encoding_error", etc.
    error_message: str | None = None
