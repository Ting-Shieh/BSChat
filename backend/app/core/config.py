from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BSChat API"
    debug: bool = False
    api_port: int = 8001
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://bschat:bschat@localhost:5433/bschat"
    redis_url: str = "redis://localhost:6380/0"

    jwt_secret: str = "dev-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000"

    enable_swagger: bool = True

    # Storage — local fallback when R2 not configured
    storage_backend: str = "local"  # local | r2
    local_upload_dir: str = "storage/uploads"
    api_base_url: str = "http://localhost:8001"

    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_public_url: str | None = None

    anthropic_api_key: str | None = None
    ocr_model: str = "claude-sonnet-4-20250514"

    # OCR provider: mock | gemini | claude
    ocr_provider: str = "mock"
    ocr_use_mock: bool = False  # set true to force mock
    gemini_api_key: str | None = None
    gemini_ocr_model: str = "gemini-2.5-flash"

    # Enrichment (M6)
    enrich_provider: str = "gemini"
    enrich_use_mock: bool = False
    gemini_enrich_model: str = "gemini-2.5-flash"
    enrich_model: str = "claude-sonnet-4-20250514"
    use_celery_workers: bool = False  # dev: in-process; prod: set true + run worker

    # Search (M5)
    search_provider: str = "gemini"
    search_use_mock: bool = False
    import_use_mock: bool = False
    search_skip_intent_parse: bool = False
    gemini_search_model: str = "gemini-2.5-flash"
    gemini_import_model: str = "gemini-2.5-flash"
    search_rerank_model: str = "claude-sonnet-4-20250514"
    search_result_limit: int = 10
    search_retrieval_limit: int = 50

    # M3 responsibility inference
    inference_use_mock: bool = False
    inference_provider: str = "gemini"
    gemini_inference_model: str = "gemini-2.5-flash"
    inference_model: str = "claude-sonnet-4-20250514"

    @property
    def effective_search_provider(self) -> str:
        if self.search_provider != "mock":
            return self.search_provider
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "claude"
        return "mock"

    @property
    def effective_inference_provider(self) -> str:
        if self.inference_provider != "mock":
            return self.inference_provider
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "claude"
        return "mock"

    @property
    def effective_enrich_provider(self) -> str:
        if self.enrich_provider != "mock":
            return self.enrich_provider
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "claude"
        return "mock"

    @property
    def effective_ocr_provider(self) -> str:
        """Resolve provider — auto-detect from API keys when provider=mock."""
        if self.ocr_provider != "mock":
            return self.ocr_provider
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "claude"
        return "mock"

    @property
    def ocr_will_use_mock(self) -> bool:
        if self.ocr_use_mock:
            return True
        provider = self.effective_ocr_provider
        if provider == "gemini":
            return not bool(self.gemini_api_key)
        if provider == "claude":
            return not bool(self.anthropic_api_key)
        return True

    @property
    def search_will_use_llm(self) -> bool:
        """Gemini/Claude for intent parse + rerank (off when SEARCH_USE_MOCK=true)."""
        if self.search_use_mock:
            return False
        return bool(self.gemini_api_key) or bool(self.anthropic_api_key)

    @property
    def import_will_use_llm(self) -> bool:
        """Gemini for digital card URL HTML extraction (off when IMPORT_USE_MOCK=true)."""
        if self.import_use_mock:
            return False
        return bool(self.gemini_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
