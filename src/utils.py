from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tomllib import load
from typing import Any

from orjson import orjson

from src.settings import get_settings

TRACE_ID: ContextVar[str] = ContextVar('TraceId')


@dataclass
class ProjectInfo:
    title: str
    version: str


@lru_cache
def get_project_info(
    pyproject_path: Path = get_settings().root_path.joinpath('pyproject.toml'),
) -> ProjectInfo:
    with pyproject_path.open('rb') as f:
        pyproject_data = load(f)

    return ProjectInfo(
        title=pyproject_data['project']['name'],
        version=pyproject_data['project']['version'],
    )


def dump_json(
    data: str | dict[str, Any] | list[dict[str, Any]],
    default: Any = None,
) -> str:
    if isinstance(data, str):
        return data

    option = orjson.OPT_NON_STR_KEYS | orjson.OPT_SORT_KEYS
    return orjson.dumps(
        data,
        default=default,
        option=option,
    ).decode()
