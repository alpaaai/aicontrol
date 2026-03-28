from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    opa_url: str = "http://localhost:8181"
    app_env: str = "development"
    secret_key: str = "changeme"
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_review_channel: str = "#aicontrol-reviews"


settings = Settings()
