from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.settings import Settings
from src.transport.rest.handlers.debug.handlers import debug_router
from src.transport.rest.middlewares.errors_handler_middleware import ErrorsHandlerMiddleware
from src.transport.rest.middlewares.trace_id_middleware import TraceIdMiddleware


def init_middlewares(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(ErrorsHandlerMiddleware, is_debug=settings.env.debug)  # type: ignore
    app.add_middleware(SessionMiddleware, secret_key=settings.env.rest.session_secret_key)  # type: ignore
    app.add_middleware(TraceIdMiddleware)  # type: ignore

    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_credentials=True,
        allow_origins=settings.env.rest.cors_allowed_origins,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def init_api_routes(app: FastAPI):
    app.include_router(debug_router)
