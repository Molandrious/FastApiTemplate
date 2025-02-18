from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI

from logger import AppLogger
from src.settings import Environment, get_settings
from src.transport import rest
from src.utils import get_project_info


@asynccontextmanager
async def _lifespan(
    app: FastAPI,  # noqa
) -> AsyncGenerator[None]:
    yield


@lru_cache
def make_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=get_project_info().title,
        redirect_slashes=False,
        lifespan=_lifespan,
        debug=settings.env.debug,
        logger=AppLogger.make(),
        docs_url='/docs' if settings.env.environment != Environment.PROD else None,
        openapi_url='/openapi.json' if settings.env.environment != Environment.PROD else None,
        redoc_url=None,
    )

    rest.init_middlewares(app=app, settings=settings)
    rest.init_api_routes(app=app)

    return app
