from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src import IS_SENTRY_INSTALLED
from src.settings import Settings
from src.utils import TRACE_ID

try:  # noqa: SIM105
    from sentry_sdk import Scope, capture_exception
except ImportError:
    pass


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        current_trace = request.headers.get(Settings().trace_id_header, str(uuid4()))
        TRACE_ID.set(current_trace)

        if IS_SENTRY_INSTALLED:
            scope: Scope = Scope.get_current_scope()
            scope.set_extra('X-Trace-Id', TRACE_ID.get())

        response = await call_next(request)
        response.headers[Settings().trace_id_header] = current_trace

        return response
