"""Central logging setup for the Helix bot."""

from __future__ import annotations

import logging


def setup_logging() -> None:
    """Configure root logging once before other modules attach loggers."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )


def get_logger(name: str = "helix") -> logging.Logger:
    return logging.getLogger(name)
