import contextlib
import sys
from pathlib import Path

from loguru import logger

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.settings import Settings  # noqa

with contextlib.suppress(ImportError):
    import uvicorn

from src.bootstrap import make_app  # noqa


def main() -> None:
    settings = Settings()
    logger.debug('some')
    uvicorn.run(
        app=make_app,
        host=settings.env.rest.host,
        port=settings.env.rest.port,
        factory=True,
        lifespan='on'
    )


if __name__ == '__main__':
    main()
