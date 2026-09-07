import logging
import re
import sys

TOKEN_REGEX = re.compile(r"(Bearer\s+|grpc\.token[=:]\s*|token[=:]\s*)([a-zA-Z0-9_\-\.]+)", re.IGNORECASE)


class SecretScrubbingFormatter(logging.Formatter):
    """Logging formatter that scrubs authentication tokens and sensitive information."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return TOKEN_REGEX.sub(r"\1[REDACTED]", original)


def get_logger(name: str) -> logging.Logger:
    """Get a categorized logger with secure formatting."""
    logger = logging.getLogger(f"aed.{name}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = SecretScrubbingFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger
