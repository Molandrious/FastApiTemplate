from abc import ABC
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from json import JSONDecodeError
from time import time

from fastapi import Request, Response
from loguru import logger
from starlette.datastructures import UploadFile

from src import IS_SENTRY_INSTALLED
from src.transport.rest.constants import LOGGING_REQUEST_METHODS_WITHOUT_BODY, LOGGING_SUBSTRINGS_OF_ROUTES_FOR_SKIP
from src.transport.rest.errors import LoggingError, ServerError
from src.utils import dump_json, get_project_info, TRACE_ID

try:  # noqa: SIM105
    from sentry_sdk import Scope, capture_exception
except ImportError:
    pass


class FastAPIRequestWrapper:
    _request_object: Request

    def __init__(
        self,
        request_object: Request,
    ) -> None:
        self._request_object = request_object

    @property
    def headers(
        self,
    ) -> str | None:
        return dump_json(dict(self._request_object.headers))

    async def get_input_data(
        self,
    ) -> str | None:
        input_data = None
        if self._request_object.method.upper() not in LOGGING_REQUEST_METHODS_WITHOUT_BODY:
            with suppress(
                UnicodeDecodeError,
                RuntimeError,
                JSONDecodeError,
            ):
                input_data = await self._request_object.json()
        if params := self._request_object.query_params:
            input_data = input_data or {}
            input_data.update(params._dict)  # noqa

        if form := await self._request_object.form():
            input_data = input_data or {}
            form_file_names = []
            for item in form._list:
                if isinstance(item[1], UploadFile):
                    form_file_names.append(str(item[1].filename))
                    continue
                input_data.update({item[0]: item[1]})
            input_data.update({'files': form_file_names})

        return dump_json(input_data) if input_data else None

    @property
    def http_method(
        self,
    ) -> str | None:
        return self._request_object.method.upper()

    @property
    def method(
        self,
    ) -> str | None:
        return str(self._request_object.url.path)

    @property
    def path(self) -> str:
        return self._request_object.url.path


class FastAPIResponseWrapper:
    _response_object: Response

    def __init__(
        self,
        response_object: Response,
    ) -> None:
        self._response_object = response_object

    @property
    def headers(
        self,
    ) -> str:
        return dump_json(dict(self._response_object.headers))

    @property
    def output_data(
        self,
    ) -> str | None:
        output_data = None
        if not self._response_object.body:
            return output_data
        with suppress(
            UnicodeDecodeError,
        ):
            output_data = self._response_object.body.decode()
        return dump_json(output_data) if output_data else None

    @property
    def status_code(
        self,
    ) -> int:
        return self._response_object.status_code


class LoggingMiddlewareBase(
    ABC,
):
    request_cls: type[FastAPIRequestWrapper]  # type: ignore
    response_cls: type[FastAPIResponseWrapper]  # type: ignore
    logging_substrings_of_routes_for_skip: Sequence[str] = ()

    async def __call__(
        self,
        request: object,
        call_next: Callable[[object], Awaitable[object]],
    ) -> object:
        wrapped_request: FastAPIRequestWrapper = self.request_cls(request)  # type: ignore
        wrapped_response: FastAPIResponseWrapper | None = None
        http_status_code = None
        start_time = time()
        error = None

        try:
            response = await call_next(request)
            wrapped_response = self.response_cls(response)  # type: ignore
            http_status_code = wrapped_response.status_code
            return response  # noqa: TRY300
        except ServerError as exc:
            error = exc
            if not http_status_code:
                http_status_code = exc.status_code
            raise
        except Exception as exc:
            error = exc
            raise
        finally:
            try:
                if not any(
                    substring
                    for substring in self.logging_substrings_of_routes_for_skip
                    if substring in wrapped_request.path
                ):
                    error_title = None
                    error_message = None
                    sentry_id = None
                    error_details = None
                    trace_id = TRACE_ID.get('UNSET')

                    if error:
                        error_title = error.title if isinstance(error, ServerError) else error.__class__.__name__
                        error_message = error.message if isinstance(error, ServerError) else str(error)
                        error_details = error.details if isinstance(error, ServerError) else None
                        sentry_id = error.sentry_id if isinstance(error, ServerError) else None

                    logger.info(
                        {
                            'destination': 'internal',
                            'http_method': wrapped_request.http_method,
                            'method': wrapped_request.method,
                            'processing_time': time() - start_time,
                            'http_status_code': http_status_code,
                            'input_data': await wrapped_request.get_input_data(),
                            'output_data': wrapped_response.output_data if wrapped_response else None,
                            'request_headers': wrapped_request.headers,
                            'response_headers': wrapped_response.headers if wrapped_response else None,
                            'error_title': error_title,
                            'error_message': error_message,
                            'error_details': error_details,
                            'sentry_id': sentry_id,
                            'trace_id': trace_id,
                            'service_version': get_project_info().version,
                        }
                    )

            except Exception as exc:
                try:
                    raise LoggingError(debug=str(exc)) from exc  # noqa
                except LoggingError as exc:
                    if IS_SENTRY_INSTALLED:
                        scope = Scope.get_current_scope()
                        scope.set_extra(exc.__class__.__name__, str(exc))
                        capture_exception(exc)


class FastAPILoggingMiddleware(
    LoggingMiddlewareBase,
):
    logging_substrings_of_routes_for_skip = LOGGING_SUBSTRINGS_OF_ROUTES_FOR_SKIP
    request_cls = FastAPIRequestWrapper
    response_cls = FastAPIResponseWrapper
