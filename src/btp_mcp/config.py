from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sap_btp_base_url: str = Field(..., alias="SAP_BTP_BASE_URL")
    sap_btp_token_url: str = Field(..., alias="SAP_BTP_TOKEN_URL")
    sap_btp_client_id: str = Field(..., alias="SAP_BTP_CLIENT_ID")
    sap_btp_client_secret: str = Field(..., alias="SAP_BTP_CLIENT_SECRET")
    sap_btp_api_path: str = Field("/api/v1", alias="SAP_BTP_API_PATH")
    sap_btp_timeout_seconds: float = Field(30.0, alias="SAP_BTP_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
