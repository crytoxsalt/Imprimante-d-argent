from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cashroll:cashroll@db:5432/cashroll"
    database_url_sync: str = "postgresql+psycopg2://cashroll:cashroll@db:5432/cashroll"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "change-me-in-production"
    nextauth_secret: str = "change-me-in-production"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_agency: str = ""
    frontend_url: str = "http://localhost:3000"
    output_dir: str = "/app/output"
    assets_dir: str = "/app/assets"

    class Config:
        env_file = ".env"


settings = Settings()
