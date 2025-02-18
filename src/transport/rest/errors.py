from starlette import status


class ServerError(Exception):
    status_code: int = 520
    message: str = 'Something went wrong'
    details: list[str] | None = None
    debug: str
    capture_by_sentry: bool = False
    sentry_id: str | None = None

    @property
    def title(self) -> str:
        return self.__class__.__name__

    def __init__(
        self,
        message: str | None = None,
        debug: str | None = None,
        details: list[str] | None = None,
    ):
        self.message = message or self.message
        self.debug = debug
        self.details = details
        super().__init__()

    def as_dict(self, *, is_debug: bool = False) -> dict:
        debug = {'debug': self.debug} if is_debug else {}
        return dict(
            title=self.title,
            message=self.message,
            details=self.details,
            **debug,
        )


class UnauthorizedError(ServerError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = 'Unauthorized'


class ForbiddenError(ServerError):
    status_code = status.HTTP_403_FORBIDDEN
    message = 'Forbidden'


class ObjectNotFoundError(ServerError):
    status_code = status.HTTP_404_NOT_FOUND
    message = 'Object not found'


class InternalValidationError(ServerError):
    status_code = status.HTTP_400_BAD_REQUEST
    message = 'Internal validation error'
    capture_by_sentry = False


class RequestValidationError(ServerError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = 'Request validation error'
    capture_by_sentry = False


class ResponseValidationError(ServerError):
    message = 'Response validation error'
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    capture_by_sentry = False


class LoggingError(ServerError):
    status_code = 500
    message = 'Внутренняя ошибка при работе c логами'
