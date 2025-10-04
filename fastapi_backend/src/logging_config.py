"""
Basic logging configuration for the FastAPI backend.

This ensures our timing logs and error diagnostics from services/chat.py and routes
are visible by default. In production, you may override this via environment or
application server configurations.
"""
import logging
import os

# PUBLIC_INTERFACE
def configure_logging(default_level: str | None = None) -> None:
    """Configure root logging level and format.

    Parameters
    ----------
    default_level : str | None
        Optional level string like "INFO", "WARNING", "DEBUG". If None, uses
        LOG_LEVEL env or falls back to INFO.
    """
    level_name = default_level or os.getenv("LOG_LEVEL", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
