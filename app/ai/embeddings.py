"""OpenAI embeddings and Pinecone I/O (async wrappers)."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from app.infra import config


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity for dedup / neighbor scoring."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def count_close_neighbors(values: list[float], all_vecs: list[list[float]], threshold: float = 0.82) -> int:
    """How many other retrieved vectors are very similar (confidence hint)."""
    n = 0
    for other in all_vecs:
        if other is values:
            continue
        if cosine_sim(values, other) >= threshold:
            n += 1
    return n


async def embed_text(text: str) -> list[float]:
    assert config.openai_client is not None
    resp = await config.openai_client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text[:8000],
    )
    return list(resp.data[0].embedding)


async def pinecone_query(**kwargs: Any) -> Any:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    return await asyncio.to_thread(lambda: idx.query(**kwargs))


async def pinecone_upsert(**kwargs: Any) -> Any:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    return await asyncio.to_thread(lambda: idx.upsert(**kwargs))


async def pinecone_delete_all_namespace(namespace: str) -> None:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    await asyncio.to_thread(lambda: idx.delete(delete_all=True, namespace=namespace))


async def pinecone_fetch_ids(ids: list[str], namespace: str) -> Any:
    assert config.pinecone_index is not None
    idx = config.pinecone_index
    return await asyncio.to_thread(lambda: idx.fetch(ids=ids, namespace=namespace))


async def pinecone_list_ids(namespace: str, limit: int = 100) -> list[str]:
    assert config.pinecone_index is not None
    idx = config.pinecone_index

    def _collect() -> list[str]:
        out_ids: list[str] = []
        for batch in idx.list(namespace=namespace, limit=limit):
            out_ids.extend(batch)
        return out_ids

    return await asyncio.to_thread(_collect)
