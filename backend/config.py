"""OpenBrief application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/openbrief"

    # Security
    secret_key: str = "change-me-in-production"
    encryption_key: str = "change-me-in-production"

    # Entity Extraction
    entity_extraction_backend: str = "prompt"
    entity_model_endpoint: str = ""

    # Embedding
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # RAG Config
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = ["http://localhost:3000"]

    # MCP Server
    mcp_server_port: int = 8001
    mcp_api_key: str = "change-me-in-production"

    # Upload
    upload_dir: str = "./uploads"
    upload_max_size_mb: int = 50

    # Full Review Strategy
    full_review_token_threshold: int = 80000


settings = Settings()
