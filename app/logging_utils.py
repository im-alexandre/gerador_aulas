from __future__ import annotations

import logging
from itertools import cycle


_COLOR_CODES = [
    "\x1b[38;5;33m",   # blue
    "\x1b[38;5;70m",   # green
    "\x1b[38;5;214m",  # orange
    "\x1b[38;5;135m",  # purple
    "\x1b[38;5;44m",   # teal
    "\x1b[38;5;203m",  # red
]
_RESET = "\x1b[0m"
_COLOR_MAP: dict[str, str] = {}
_COLOR_POOL = cycle(_COLOR_CODES)


def _color_for_thread(name: str) -> str:
    if name not in _COLOR_MAP:
        _COLOR_MAP[name] = next(_COLOR_POOL)
    return _COLOR_MAP[name]


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        color = _color_for_thread(record.threadName or "main")
        return f"{color}{base}{_RESET}"


class SuppressNoisyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "STREAM" in msg or "b'" in msg:
            return False
        return True


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    formatter = ColorFormatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    filter_noisy = SuppressNoisyFilter()
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)
        handler.addFilter(filter_noisy)

    if not verbose:
        for noisy in ("httpx", "openai", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    else:
        for noisy in ("httpx", "openai", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.INFO)


def log_step(
    logger: logging.Logger,
    context: str,
    func_name: str,
    message: str,
    *,
    level: int = logging.INFO,
) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.log(level, f"[{context}] ({func_name}) {message}")
    else:
        logger.log(level, f"[{context}] {message}")
