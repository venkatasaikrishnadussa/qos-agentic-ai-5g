from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    environment: Literal["local", "dev", "staging", "prod"] = Field(
        default="local", validation_alias="ENVIRONMENT"
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    service_name: str = Field(
        default="5g-agentic-policy-optimizer", validation_alias="SERVICE_NAME"
    )
    openai_api_key: Optional[str] = Field(
        default=None, validation_alias="OPENAI_API_KEY"
    )
    prometheus_port: int = Field(default=8001, validation_alias="PROMETHEUS_PORT")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    pcf_base_url: str = Field(
        default="http://localhost:8000", validation_alias="PCF_BASE_URL"
    )

    model_config = {"extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Load settings from environment variables.
    """
    return Settings()  # type: ignore[arg-type]


settings = get_settings()

