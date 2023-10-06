import os
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseConfig

load_dotenv(find_dotenv())


class GlobalConfig(BaseConfig):
    title: str = os.environ.get("TITLE")
    version: str = "1.0.0"
    description: str = os.environ.get("DESCRIPTION")
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    api_prefix: str = "/api"
    debug: bool = os.environ.get("DEBUG")

    postgres_user: str = os.environ.get("POSTGRES_USER")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD")
    postgres_host: str = os.environ.get("POSTGRES_HOST")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT"))
    postgres_db: str = os.environ.get("POSTGRES_DB")
    postgres_db_tests: str = os.environ.get("POSTGRES_DB_TESTS")
    db_echo_log: bool = True if os.environ.get("DEBUG") == "True" else False

    redis_server: str = os.environ.get("REDIS_SERVER")
    redis_port: int = int(os.environ.get("REDIS_PORT"))

    access_token_expire_minutes: str = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))
    refresh_token_expire_minutes: str = int(os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES"))
    password_hash_algorithm: str = os.environ.get("PASSWORD_HASH_ALGORITHM")
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY")
    jwt_refresh_secret_key: str = os.environ.get("JWT_REFRESH_SECRET_KEY")

    @property
    def sync_database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = GlobalConfig()
