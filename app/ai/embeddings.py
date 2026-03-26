"""OpenAI embeddings and Pinecone I/O (async wrappers)."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from app.infra import config


# ------
#   measures how similar two vectors are, returning a value between 0 and 1.
#
# -------

def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity for dedup / neighbor scoring."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

# ------
#  confidence signal: one vector and checks how many other retrieved vectors are very similar to it (threshold: 0.82)
# -------

def count_close_neighbors(values: list[float], all_vecs: list[list[float]], threshold: float = 0.82) -> int:
    """How many other retrieved vectors are very similar (confidence hint)."""
    n = 0
    for other in all_vecs:
        if other is values:
            continue
        if cosine_sim(values, other) >= threshold:
            n += 1
    return n




# ------
#   embeds text into a vector using the OpenAI API, sends a string of text to OpenAI and gets back a vector 
# -------
async def embed_text(text: str) -> list[float]:
    assert config.openai_client is not None
    resp = await config.openai_client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text[:8000],
    )
    return list(resp.data[0].embedding)

# ------
#   SEARCH === searches the database for vectors similar to a query vector
# -------
async def pinecone_query(**kwargs: Any) -> Any:                         # **kwargs: Any allows for any number of keyword arguments to be passed in
    assert config.pinecone_index is not None                            # safety check
    idx = config.pinecone_index                                         # # grab the connection, pinecone index
    return await asyncio.to_thread(lambda: idx.query(**kwargs))         # run it: lambda wraps the call into a funciton

# ------
#   WRITE === writes vectors into the database. "Upsert" = update if exists, insert if not. Used when saving a new memory.
# -------

async def pinecone_upsert(**kwargs: Any) -> Any:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    return await asyncio.to_thread(lambda: idx.upsert(**kwargs))

# ------
#   DELETE === deletes every vector in a namespace (a user's entire memory). The namespace here maps to a Telegram user ID, so this is essentially "wipe all memory for this user."
# -------
async def pinecone_delete_all_namespace(namespace: str) -> None:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    await asyncio.to_thread(lambda: idx.delete(delete_all=True, namespace=namespace))
# ------
#   FETCH === retrieves specific vectors by their exact IDs,
# -------

async def pinecone_fetch_ids(ids: list[str], namespace: str) -> Any:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    return await asyncio.to_thread(lambda: idx.fetch(ids=ids, namespace=namespace))
# ------
#   LIST === lists all the IDs stored for a user without fetching the actual vector data. 
# Set limit at 100 for balanced call for each user 
# -------

async def pinecone_list_ids(namespace: str, limit: int = 100) -> list[str]:
    assert config.pinecone_index is not None
    idx = config.pinecone_index

    def _collect() -> list[str]:
        out_ids: list[str] = []
        for batch in idx.list(namespace=namespace, limit=limit):
            out_ids.extend(batch)
        return out_ids

    return await asyncio.to_thread(_collect)
