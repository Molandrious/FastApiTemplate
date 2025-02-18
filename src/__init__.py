IS_SENTRY_INSTALLED = True

try:
    import sentry_sdk
except ImportError:
    IS_SENTRY_INSTALLED = False
