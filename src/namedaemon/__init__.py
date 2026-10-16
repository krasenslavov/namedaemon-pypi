"""Client and CLI for NameDaemon (https://namedaemon.com)."""

__version__ = "0.1.1"

from .client import (  # noqa: E402
    DEFAULT_BASE_URL,
    NameDaemon,
    NameDaemonError,
    RateLimitError,
)

__all__ = ["NameDaemon", "NameDaemonError", "RateLimitError", "DEFAULT_BASE_URL", "__version__"]
