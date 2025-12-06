import os
from enum import Enum


class LogLevel(Enum):
    NONE = 0
    INFO = 1
    DEBUG = 2


# Set global log level here or via environment variable
LOG_LEVEL = os.environ.get("RECOMMENDER_LOG_LEVEL", "INFO").upper()
if LOG_LEVEL == "DEBUG":
    LOG_LEVEL = LogLevel.DEBUG
elif LOG_LEVEL == "NONE":
    LOG_LEVEL = LogLevel.NONE
else:
    LOG_LEVEL = LogLevel.INFO


# ANSI color codes
LOG_COLORS = {
    LogLevel.INFO: "\033[94m",  # Blue
    LogLevel.DEBUG: "\033[92m",  # Green
    LogLevel.NONE: "",
}
RESET_COLOR = "\033[0m"


def log(msg, level=LogLevel.INFO):
    if LOG_LEVEL == LogLevel.NONE:
        return
    if LOG_LEVEL == LogLevel.INFO and level == LogLevel.DEBUG:
        return
    color = LOG_COLORS.get(level, "")
    print(f"{color}[LOG][{level.name}] {msg}{RESET_COLOR}")
