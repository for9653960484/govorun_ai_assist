from __future__ import annotations

import json
from pathlib import Path

from app.core.types import RetrievedChunk


class Retriever:
    """Поиск релевантных фрагментов по ключевым словам."""

    def search(self, index_path: Path, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        items = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
        q_words = set(query.lower().split())
        scored: list[RetrievedChunk] = []
        for item in items:
            text = item["text"]
            words = set(text.lower().split())
            score = float(len(q_words & words))
            if score > 0:
                scored.append(
                    RetrievedChunk(source=index_path, chunk_id=item["id"], text=text, score=score)
                )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
