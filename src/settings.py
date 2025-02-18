from enum import auto, StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, DirectoryPath, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

UpperStr = Annotated[str, AfterValidator(lambda v: v.upper())]


# https://docs.pydantic.dev/latest/concepts/pydantic_settings/#environment-variable-names


class Environment(StrEnum):
    @classmethod
    def _missing_(cls, value: str) -> str | None:
        value_lower = value.lower()
        for member in cls:
            if member.name.lower() == value_lower:
                return member
        return None

    LOCAL = auto()
    DEV = auto()
    PROD = auto()


class _BaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
        str_strip_whitespace=True,
        validate_default=True,
        case_sensitive=False,
    )


class LoggerSettings(_BaseSettings):
    path: Path = Field(default=Path('../logs/app.log'))
    rotation: str = Field(default='1 day')
    retention: str = Field(default='1 month')
    compression: str = Field(default='zip')
    encoding: str = Field(default='utf-8')
    level: UpperStr = Field(default='info')


class RESTSettings(_BaseSettings):
    host: str = Field(default='127.0.0.1')
    port: int = Field(default=8000)
    session_secret_key: str = Field(default='some secret key')
    cors_allowed_origins: list[str] = Field(default=['*'])


class TestsSettings(_BaseSettings):
    create_docker_postgres_for_tests: bool = Field(default=False)
    local_test_db_dsn: PostgresDsn = Field(default='postgresql+asyncpg://root:15243@localhost:5432/testdb')
    docker_test_db_dsn: PostgresDsn = Field(default='postgresql+asyncpg://testuser:testpassword@localhost:5433/testdb')


class EnvSettings(_BaseSettings):
    environment: Environment = Field(default=Environment.LOCAL)
    rest: RESTSettings = RESTSettings(_env_prefix='REST_')
    logger: LoggerSettings = LoggerSettings(_env_prefix='LOGGER_')
    tests: TestsSettings = TestsSettings(_env_prefix='TEST')
    # postgres_dsn: PostgresDsn = Field()
    # redis_dsn: RedisDsn = Field()
    sentry_dsn: str = Field(default='')
    debug: bool = Field(default=False)


class Settings(BaseModel):
    env: EnvSettings = EnvSettings()
    root_path: DirectoryPath = Path(__file__).parent.parent.resolve()
    logs_path: DirectoryPath = root_path.joinpath('logs')
    trace_id_header: str = Field(default='X-Request-ID')
    sentry_id_header: str = Field(default='X-Sentry-ID')


@lru_cache
def get_settings() -> Settings:
    return Settings()
