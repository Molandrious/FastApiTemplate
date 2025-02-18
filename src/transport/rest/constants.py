SKIP_MIDDLEWARE_PATHS = ('/healthcheck', '/api/docs', '/redoc', '/api/openapi.json', '/metrics')

LOGGING_REQUEST_METHODS_WITHOUT_BODY = {'GET', 'DELETE'}
LOGGING_SUBSTRINGS_OF_ROUTES_FOR_SKIP = (
    'metrics',
)
