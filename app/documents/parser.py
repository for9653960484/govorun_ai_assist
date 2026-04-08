from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from docx import Document


class DocumentParser:
    """Парсер файлов в сырой текст."""

    def parse(self, src_path: Path) -> str:
        suffix = src_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return src_path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            reader = PdfReader(str(src_path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if suffix == ".docx":
            doc = Document(str(src_path))
            return "\n".join(p.text for p in doc.paragraphs)
        raise ValueError(f"Неподдерживаемый формат: {suffix}")
