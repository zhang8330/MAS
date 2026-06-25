from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="ArchMAS Backend", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    pro_mas_root: str = Field(default="", alias="PRO_MAS_ROOT")
    pro_mas_python: str = Field(default="", alias="PRO_MAS_PYTHON")
    ccg_dataset_db_path: str = Field(default="dataset.db", alias="CCG_DATASET_DB_PATH")
    knomas_data_root: str = Field(default="data/data", alias="KNOMAS_DATA_ROOT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
