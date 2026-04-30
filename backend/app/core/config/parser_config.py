from pydantic_settings import BaseSettings, SettingsConfigDict


class ParserConfig(BaseSettings):
    """
    Configuration for document parsers.
    """

    ingestion_allowed_file_types: list[str] = [".md", ".txt", ".pdf", ".docx"]
    parser_pdf_enabled: bool = True
    parser_docx_enabled: bool = True
    parser_spreadsheet_enabled: bool = False
    parser_ocr_enabled: bool = False

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )
