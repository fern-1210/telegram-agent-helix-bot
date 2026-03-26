"""Central logging setup for the Helix bot."""


# -----------------
#
# operability (debugging, auditing that memory writes failed, etc.)
# app/main.py: mports and runs setup_logging() first, then uses get_logger for the bot startup line.
# app/infra/config.py: Uses get_logger("helix") for Pinecone init failures, missing-keys warnings, etc.
# app/bot/handlers.py: uses get_logger for Claude API errors.
# app/ai/memory.py: uses get_logger for memory write skips and errors.
# app/bot/commands.py: uses get_logger for memory debug command failures.
# app/bot/access.py: uses get_logger for access control checks.
# app/ai/embeddings.py: uses get_logger for Pinecone init warnings.
# app/ai/embeddings.py: uses get_logger for Pinecone query errors.
# app/ai/embeddings.py: uses get_logger for Pinecone upsert errors.
# -----------




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
