from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from src.transport.rest.middlewares.logging_middleware import FastAPILoggingMiddleware


class _FastAPILoggingRoute(
    APIRoute,
):
    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        middleware = FastAPILoggingMiddleware()
        original_route_handler = super().get_route_handler()
        return partial(
            middleware,
            call_next=original_route_handler,
        )


class FastAPILoggingRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('default_response_class'):
            kwargs['default_response_class'] = ORJSONResponse

        if not kwargs.get('route_class'):
            kwargs['route_class'] = _FastAPILoggingRoute

        super().__init__(*args, **kwargs)
