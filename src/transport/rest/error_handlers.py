from functools import partial

from fastapi import FastAPI, Request
from fastapi.exceptions import (
    RequestValidationError as FastAPIRequestValidationError,
    ResponseValidationError as FastAPIResponseValidationError,
)
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.responses import Response

from src import IS_SENTRY_INSTALLED
from src.settings import Settings
from src.transport.rest.errors import (
    InternalValidationError,
    RequestValidationError,
    ResponseValidationError,
    ServerError,
)

try:  # noqa: SIM105
    from sentry_sdk import Scope, capture_exception
except ImportError:
    pass



def prepare_server_exc(
    exc: ServerError,
    trace_id: str | None = None,
    sentry_id: str | None = None,
) -> None:
    if not IS_SENTRY_INSTALLED:
        return

    if exc.capture_by_sentry and not exc.sentry_id:
        scope = Scope.get_current_scope()
        if trace_id:
            scope.set_tag(Settings().trace_id_header.lower(), trace_id)
        scope.set_extra('server_error.title', exc.title)
        scope.set_extra('server_error.message', exc.message)
        sentry_id = capture_exception(exc)
    if sentry_id and not exc.sentry_id:
        exc.sentry_id = sentry_id


def process_server_error(
    request: Request,
    exc: ServerError,
    *,
    sentry_id: str | None,
    is_debug: bool,
    old_exc: Exception | None = None,
) -> Response:
    trace_id = request.headers.get(Settings().trace_id_header)

    if old_exc and not exc.debug:
        exc.debug = str(old_exc)

    prepare_server_exc(
        exc=exc,
        trace_id=trace_id,
        sentry_id=sentry_id,
    )

    response: JSONResponse = JSONResponse(
        content=exc.as_dict(is_debug=is_debug),
        status_code=exc.status_code,
        headers={Settings().sentry_id_header: sentry_id} if sentry_id else None,
    )
    return response


def _redefine_error(
    request: Request,
    exc: Exception,
    server_error_instance: ServerError,
    *,
    is_debug: bool,
) -> Response:
    return process_server_error(
        request=request,
        exc=server_error_instance,
        sentry_id=None,
        is_debug=is_debug,
        old_exc=exc,
    )


def _make_server_error_instance(
    exc_class_or_status_code: int | type[Exception],
    server_error_type: type[ServerError],
) -> ServerError:
    if isinstance(exc_class_or_status_code, int):
        debug_info = f'redefined internal http status {exc_class_or_status_code}'
        return ServerError(debug=debug_info) if not server_error_type else server_error_type(debug=debug_info)

    return ServerError() if not server_error_type else server_error_type()


def _cast_exc_class_or_status_code_to_list(
    exc_class_or_status_codes: int | list[int] | type[Exception] | list[type[Exception]],
) -> list[int | type[Exception]]:
    if not isinstance(exc_class_or_status_codes, list):
        exc_class_or_status_codes = [exc_class_or_status_codes]
    return exc_class_or_status_codes


def _redefine_internal_exception(
    app: FastAPI,
    exc_class_or_status_codes: int | list[int] | type[Exception] | list[type[Exception]],
    server_error_type: type[ServerError] | None,
    *,
    is_debug: bool,
) -> None:
    for exc_class_or_status_code in _cast_exc_class_or_status_code_to_list(exc_class_or_status_codes):
        if not server_error_type and isinstance(exc_class_or_status_code, int):
            raise ValueError
        if not server_error_type:
            app.add_exception_handler(
                exc_class_or_status_code=exc_class_or_status_code,
                handler=partial(
                    _redefine_error,
                    is_debug=is_debug,
                    server_error_instance=exc_class_or_status_codes,
                ),
            )
            continue
        app.add_exception_handler(
            exc_class_or_status_code=exc_class_or_status_code,
            handler=partial(
                _redefine_error,
                is_debug=is_debug,
                server_error_instance=_make_server_error_instance(
                    exc_class_or_status_code=exc_class_or_status_code,
                    server_error_type=server_error_type,
                ),
            ),
        )


def setup_fastapi_error_handlers(
    app: FastAPI,
    *,
    is_debug: bool,
) -> None:
    app.add_exception_handler(
        exc_class_or_status_code=ServerError,
        handler=partial(
            process_server_error,
            is_debug=is_debug,
            sentry_id=None,
        ),
    )
    _redefine_internal_exception(
        app=app,
        is_debug=is_debug,
        exc_class_or_status_codes=FastAPIRequestValidationError,
        server_error_type=RequestValidationError,
    )
    _redefine_internal_exception(
        app=app,
        is_debug=is_debug,
        exc_class_or_status_codes=FastAPIResponseValidationError,
        server_error_type=ResponseValidationError,
    )
    _redefine_internal_exception(
        app=app,
        is_debug=is_debug,
        exc_class_or_status_codes=PydanticValidationError,
        server_error_type=InternalValidationError,
    )
