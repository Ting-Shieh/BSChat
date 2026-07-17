from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "BSChat API"
    debug: bool = False
    api_port: int = 8001
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://bschat:bschat@localhost:5433/bschat"
    redis_url: str = "redis://localhost:6380/0"

    jwt_secret: str = "dev-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # Auth: dev-login local only; Google OAuth + magic link for team
    allow_dev_login: bool = True
    dogfood_default_plan: str = "pro"
    # Enterprise ops (provision / approve). Empty + allow_dev_login → local dogfood OK.
    enterprise_ops_token: str | None = None
    frontend_base_url: str = "http://localhost:3000"
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None  # e.g. http://localhost:8001/api/v1/auth/google/callback
    auth_email_domain_allowlist: str = ""  # comma domains; empty = any
    magic_link_expire_minutes: int = 30
    # Email: auto prefers SMTP when configured, else Resend.
    email_provider: str = "auto"  # auto | smtp | resend
    resend_api_key: str | None = None
    resend_from_email: str | None = None
    # Gmail SMTP (App Password). Host default smtp.gmail.com:587 STARTTLS.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None  # full Gmail address
    smtp_password: str | None = None  # 16-char App Password
    smtp_from_email: str | None = None  # e.g. BSChat <you@gmail.com>

    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:3002,http://127.0.0.1:3002"
    )

    enable_swagger: bool = True

    # Storage — local | neon | s3 | r2
    storage_backend: str = "local"
    local_upload_dir: str = "storage/uploads"
    api_base_url: str = "http://localhost:8001"
    storage_public_base_url: str | None = None  # media origin; defaults to r2_public_url or api_base_url

    # Neon Object Storage / generic S3 (boto3). Neon Console → Credentials also emits AWS_* names.
    s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"),
    )
    s3_access_key_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"),
    )
    s3_secret_access_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"),
    )
    s3_bucket_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_BUCKET_NAME", "NEON_STORAGE_BUCKET"),
    )
    s3_region: str = Field(
        default="us-east-2",
        validation_alias=AliasChoices("S3_REGION", "AWS_REGION"),
    )

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
    search_rerank_input_max: int = 60
    search_embedding_enabled: bool = True
    search_embedding_model: str = "text-embedding-004"
    search_embedding_dims: int = 768
    search_embedding_use_mock: bool = False
    search_embedding_fallback_mock: bool = True
    search_embedding_timeout_s: float = 15.0
    search_hybrid_rrf_k: int = 60
    search_debug_enabled: bool = False

    # M3 responsibility inference
    inference_use_mock: bool = False
    inference_provider: str = "gemini"
    gemini_inference_model: str = "gemini-2.5-flash"
    inference_model: str = "claude-sonnet-4-20250514"

    # M3.5 person enrichment (Pro: LinkedIn + LLM)
    person_enrich_use_mock: bool = False
    person_enrich_provider: str = "gemini"  # gemini | claude | mock (LLM summarize)
    person_search_provider: str = "mock"  # mock | linkedin (official API, not wired yet)
    person_linkedin_web_fallback: bool = True  # Gemini Google Search for user-provided LinkedIn URLs
    person_web_lookup_timeout_s: float = 20.0  # 同步請求內的 web 查詢逾時（避免 HTTP 掛太久）
    gemini_person_model: str = "gemini-2.5-flash"
    person_enrich_model: str = "claude-sonnet-4-20250514"
    person_match_gate: float = 0.8
    person_confidence_gate: float = 0.75  # linkedin_url | people_api
    person_confidence_gate_web: float = 0.70  # web_search on known LinkedIn URL
    person_confidence_gate_card: float = 0.65  # card_inference fallback

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
    def effective_person_enrich_provider(self) -> str:
        if self.person_enrich_provider != "mock":
            return self.person_enrich_provider
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
