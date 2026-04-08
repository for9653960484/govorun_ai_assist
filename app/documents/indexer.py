from __future__ import annotations

import json
from pathlib import Path


class DocumentIndexer:
    """Простой индексатор документов по чанкам."""

    def __init__(self, chunk_size: int = 700, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _chunk(self, text: str) -> list[str]:
        if not text:
            return []
        out: list[str] = []
        i = 0
        while i < len(text):
            out.append(text[i : i + self.chunk_size])
            i += max(1, self.chunk_size - self.overlap)
        return out

    def build_index(self, doc_id: str, text: str, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        chunks = self._chunk(text)
        payload = [{"id": f"{doc_id}:{i}", "text": c} for i, c in enumerate(chunks)]
        index_path = out_dir / f"{doc_id}.json"
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return index_path
