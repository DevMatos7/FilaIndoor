from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "REAL Fila & Indoor"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480
    database_url: str = "postgresql+psycopg://fila:fila@localhost:5455/filaindoor"
    cors_origins: str = "http://localhost:5180,http://127.0.0.1:5180"
    default_admin_email: str = "admin@real.local"
    default_admin_password: str = "admin123"
    jwt_algorithm: str = "HS256"

    # Impressão (Sprint 2) — mock por padrão no Docker
    print_provider: str = "mock"  # mock | escpos | fail
    printer_host: str = "host.docker.internal"
    printer_port: int = 9100
    printer_timeout_seconds: float = 3.0
    default_kiosk_token: str = "kiosk-acougue-demo"

    # Mídia (Sprint 7) — storage local
    media_root: str = "storage/media"
    media_max_image_mb: int = 10
    media_max_video_mb: int = 100
    media_public_prefix: str = "/media/files"

    # ERP / CISS (Sprint 12) — somente leitura
    erp_provider: str = "mock"  # mock | ciss_api | ciss_db2
    ciss_api_base_url: str = ""
    ciss_api_key: str = ""
    ciss_db2_dsn: str = ""
    erp_price_sync_minutes: int = 10
    erp_stock_sync_minutes: int = 20
    erp_only_in_stock_min_qty: float = 0.01

    # DRC-1 Retail Data Foundation — CISS DB2 read-only
    # Fonte operacional: backend/.env
    #   DB2_CONN_STRING  (ODBC sem DRIVER=)
    #   DB2_SCHEMA / DB2_FALLBACK_HOST / DB2_FALLBACK_PORT / IBM_DB_HOME
    retail_provider: str = "mock"  # mock | ciss_db2
    db2_conn_string: str = ""  # DATABASE=...;HOSTNAME=...;PORT=...;UID=...;PWD=...;SCHEMA=...
    db2_schema: str = "DBA"
    db2_fallback_host: str = ""
    db2_fallback_port: int = 50044
    ibm_db_home: str = ""
    db2_odbc_driver: str = "IBM DB2 ODBC DRIVER"
    db2_query_timeout_seconds: float = 30.0
    retail_warn_after_seconds: int = 300
    retail_hard_stop_after_seconds: int = 900
    retail_sync_product_limit: int = 2000
    retail_sync_price_limit: int = 5000

    # DRC-5 Automation — intervals independent from freshness thresholds
    retail_automation_enabled: bool = True
    retail_sync_product_seconds: int = 900
    retail_sync_price_seconds: int = 60
    retail_sync_promotion_seconds: int = 60
    retail_sync_availability_seconds: int = 180
    retail_sync_offer_seconds: int = 120
    retail_sync_product_image_seconds: int = 900
    retail_sync_price_chain_seconds: int = 900
    retail_allow_mock_in_production: bool = False

    @property
    def is_production(self) -> bool:
        return (self.app_env or "").strip().lower() in {"production", "prod"}

    # Toledo (S13 discovery + S14 adapter)
    toledo_enabled: bool = False
    toledo_mode: str = "NATIVE"  # NATIVE | TOLEDO_DISPLAY | TOLEDO_SYNC | TOLEDO_FULL
    toledo_api_base_url: str = ""
    toledo_api_key: str = ""
    toledo_mock: bool = False  # testes / POC sem rede

    # REAL+ / fila virtual (Sprint 15)
    real_plus_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
