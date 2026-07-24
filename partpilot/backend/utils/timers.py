"""Timing utilities for measuring pipeline stage latency.

Pure infrastructure (no AI logic), so implemented directly rather than
left as a stub.
"""

import functools
import time
from collections.abc import Callable
from types import TracebackType
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class Timer:
    """Context manager that measures elapsed wall-clock time in milliseconds.

    Example:
        with Timer() as t:
            do_work()
        print(t.elapsed_ms)
    """

    def __init__(self) -> None:
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


def timed(func: F) -> F:
    """Decorator that logs how long a function took to execute.

    Uses the caller's module logger so timing output is consistent with
    the rest of the application's log format.
    """
    from backend.core.logging import get_logger

    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with Timer() as t:
            result = func(*args, **kwargs)
        logger.debug("%s took %.2fms", func.__qualname__, t.elapsed_ms)
        return result

    return wrapper  # type: ignore[return-value]
