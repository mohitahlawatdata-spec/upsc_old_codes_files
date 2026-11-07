"""Terminal diagnostics without essay text or credentials."""

import logging
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

logger = logging.getLogger("mainsmaster")


def configure_logging() -> None:
    """Send application stage events to the VS Code terminal once per process."""
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


@contextmanager
def stage(name: str, progress: Callable[[str], None] | None = None) -> Iterator[None]:
    if progress:
        progress(name)
    logger.info("START %s", name)
    started = time.monotonic()
    try:
        yield
    except Exception as exc:
        logger.error(
            "FAILED %s after %.1fs (%s)", name, time.monotonic() - started, type(exc).__name__
        )
        raise
    else:
        logger.info("DONE %s in %.1fs", name, time.monotonic() - started)
