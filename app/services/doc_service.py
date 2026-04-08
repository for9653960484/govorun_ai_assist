from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.documents.cleaner import TextCleaner
from app.documents.indexer import DocumentIndexer
from app.documents.parser import DocumentParser
from app.documents.retriever import Retriever


class DocumentService:
    """Сервис конвейера загрузки и поиска по документам."""

    def __init__(self) -> None:
        self.parser = DocumentParser()
        self.cleaner = TextCleaner()
        self.indexer = DocumentIndexer()
        self.retriever = Retriever()
        self._last_index_by_user: dict[str, Path] = {}

    def ingest(self, user_id: str, src_file: Path) -> dict:
        doc_id = f"{user_id}_{src_file.stem}"
        raw_text = self.parser.parse(src_file)
        clean_text = self.cleaner.clean(raw_text)

        parsed_path = settings.documents_parsed_dir / f"{doc_id}.txt"
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_path.write_text(clean_text, encoding="utf-8")

        index_path = self.indexer.build_index(doc_id, clean_text, settings.documents_index_dir)
        self._last_index_by_user[user_id] = index_path
        return {
            "doc_id": doc_id,
            "parsed_path": str(parsed_path),
            "index_path": str(index_path),
            "chunks": len(self.indexer._chunk(clean_text)),
        }

    def answer_with_doc(self, index_path: Path, question: str) -> list[dict]:
        chunks = self.retriever.search(index_path=index_path, query=question, top_k=3)
        return [
            {"chunk_id": c.chunk_id, "text": c.text, "score": c.score, "source": str(c.source)}
            for c in chunks
        ]

    def get_last_index_path(self, user_id: str) -> Path | None:
        return self._last_index_by_user.get(user_id)
