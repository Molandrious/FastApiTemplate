from traceback import format_exc, print_exc

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.settings import Settings
from src.transport.rest.error_handlers import IS_SENTRY_INSTALLED, process_server_error
from src.transport.rest.errors import ServerError

try:  # noqa: SIM105
    from sentry_sdk import Scope, capture_exception
except ImportError:
    pass


class ErrorsHandlerMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        *args,
        is_debug: bool,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.is_debug = is_debug

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = Settings()
        try:
            return await call_next(request)
        except ServerError as exc:
            return process_server_error(
                request=request,
                exc=exc,
                sentry_id=None,
                is_debug=self.is_debug,
            )
        except Exception as exc:
            print_exc()
            sentry_id = None

            if IS_SENTRY_INSTALLED:
                scope = Scope.get_current_scope()
                if trace_id := request.scope.get(settings.trace_id_header):
                    scope.set_tag(settings.trace_id_header, trace_id)
                sentry_id = capture_exception(exc)

            return process_server_error(
                request=request,
                exc=ServerError(debug=format_exc()),
                sentry_id=sentry_id,
                is_debug=self.is_debug,
            )
