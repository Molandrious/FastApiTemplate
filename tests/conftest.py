import asyncio
import contextlib
import sys
from asyncio import AbstractEventLoop
from collections.abc import Generator
from contextlib import nullcontext
from typing import Any, Generator
from unittest.mock import patch
from uuid import UUID, uuid4

import nest_asyncio
import pytest
import sqlalchemy
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from httpx import AsyncClient
from loguru import logger
from pytest_docker.plugin import get_docker_services
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.bootstrap import make_app
from src.database.client import SQLAlchemyClient
from src.integrations.ory_kratos.models import UserIdentity

# from src.database.init_test_db import TestDB
from src.settings import get_settings, Settings
from src.utils import TRACE_ID
from tests.factories.base import FactorySession
from tests.utils.test_db import TestDB


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.anyio)


def pytest_configure(config):  # noqa
    settings = get_settings()
    settings.env.sentry_dsn = ''
    if settings.env.tests.create_docker_postgres_for_tests:
        settings.env.postgres_dsn = settings.env.tests.docker_test_db_dsn
    else:
        settings.env.postgres_dsn = settings.env.tests.local_test_db_dsn

    engine = sqlalchemy.create_engine(
        url=settings.env.postgres_dsn.unicode_string().replace('postgresql+asyncpg', 'postgresql')
    )

    FactorySession.configure(bind=engine)


@pytest.fixture(scope='session')
async def _init_test_db_docker_container(
    docker_compose_command: str,
    docker_compose_project_name: str,
    docker_setup: str,
    docker_cleanup: str,
    settings: Settings,
) -> None:
    docker_service_cm = (
        get_docker_services(
            docker_compose_command,
            settings.root_path.joinpath('tests/testdb-docker-compose.yml'),
            docker_compose_project_name,
            docker_setup,
            docker_cleanup,
        )
        if Settings().env.tests.create_docker_postgres_for_tests
        else nullcontext()
    )

    with docker_service_cm as docker_service:
        with contextlib.suppress(AttributeError):
            docker_service.wait_until_responsive(check=is_postgres_responsive, timeout=10, pause=1)  # noqa
            logger.debug('Postgres container created')
        yield


@pytest.fixture(scope='session', autouse=True)
async def _do_migrations_for_test_db(_init_test_db_docker_container) -> None:
    postgres_dsn = Settings().env.postgres_dsn.unicode_string()

    alembic_cfg = Config(Settings().root_path.joinpath('alembic.ini'))
    if 'localhost' in postgres_dsn:
        alembic_cfg.set_main_option('script_location', '../migrations')
        command.downgrade(alembic_cfg, 'base')
        (command.upgrade(alembic_cfg, 'head'))



@pytest.fixture(scope='session', autouse=True)
def anyio_backend(request):  # noqa
    return 'asyncio'


@pytest.fixture(scope='session', autouse=True)
def event_loop() -> Generator[AbstractEventLoop, Any, None]:
    logger.debug('Setting event loop')
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    nest_asyncio.apply()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _set_test_trace_id() -> Generator[str, Any, None]:
    token = TRACE_ID.set(str(uuid4()))
    yield TRACE_ID.get()
    TRACE_ID.reset(token)


@pytest.fixture(scope='session')
async def settings() -> Settings:
    return Settings()


@pytest.fixture()
async def app() -> FastAPI:
    return make_app()


@pytest.fixture()
async def test_client(app: FastAPI):
    async with AsyncClient(app=app, base_url='http://test') as client:
        yield client
