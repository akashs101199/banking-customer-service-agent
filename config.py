"""
Application Configuration Management
Loads and validates configuration from environment variables
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = Field(default="Banking Customer Service AI", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./banking_ai.db",
        alias="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    
    # LLM Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")
    ollama_temperature: float = Field(default=0.7, alias="OLLAMA_TEMPERATURE")
    ollama_max_tokens: int = Field(default=2048, alias="OLLAMA_MAX_TOKENS")
    
    # Vector Database
    chroma_persist_directory: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="banking_conversations", alias="CHROMA_COLLECTION_NAME")
    
    # Security
    secret_key: str = Field(default="change-this-secret-key", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    encryption_key: str = Field(default="change-this-encryption-key", alias="ENCRYPTION_KEY")
    
    # Banking
    bank_name: str = Field(default="OpenBank AI", alias="BANK_NAME")
    bank_code: str = Field(default="OBANK", alias="BANK_CODE")
    account_number_prefix: str = Field(default="ACC", alias="ACCOUNT_NUMBER_PREFIX")
    card_number_prefix: str = Field(default="4532", alias="CARD_NUMBER_PREFIX")
    
    # KYC
    kyc_required_documents: List[str] = Field(
        default=["id_proof", "address_proof", "photo"],
        alias="KYC_REQUIRED_DOCUMENTS"
    )
    kyc_auto_approval_threshold: float = Field(default=0.85, alias="KYC_AUTO_APPROVAL_THRESHOLD")
    max_document_size_mb: int = Field(default=5, alias="MAX_DOCUMENT_SIZE_MB")
    
    # Fraud Detection
    fraud_detection_enabled: bool = Field(default=True, alias="FRAUD_DETECTION_ENABLED")
    fraud_score_threshold: float = Field(default=0.7, alias="FRAUD_SCORE_THRESHOLD")
    max_daily_transaction_amount: float = Field(default=50000.0, alias="MAX_DAILY_TRANSACTION_AMOUNT")
    max_transaction_count_per_day: int = Field(default=20, alias="MAX_TRANSACTION_COUNT_PER_DAY")
    
    # Compliance
    aml_screening_enabled: bool = Field(default=True, alias="AML_SCREENING_ENABLED")
    transaction_monitoring_enabled: bool = Field(default=True, alias="TRANSACTION_MONITORING_ENABLED")
    audit_log_retention_days: int = Field(default=2555, alias="AUDIT_LOG_RETENTION_DAYS")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: str = Field(default="./logs/banking_ai.log", alias="LOG_FILE")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    
    # OCR
    tesseract_path: str = Field(default="/usr/bin/tesseract", alias="TESSERACT_PATH")
    ocr_language: str = Field(default="eng", alias="OCR_LANGUAGE")
    
    @validator("kyc_required_documents", pre=True)
    def parse_list(cls, v):
        """Parse comma-separated string to list"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
