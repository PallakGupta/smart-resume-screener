"""Extract raw text from PDF and plain-text resume files."""

from pathlib import Path

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Allowed: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    if suffix == ".pdf":
        return _extract_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    combined = "\n\n".join(parts).strip()
    if not combined:
        raise ValueError(
            "Could not extract text from PDF. The file may be scanned/image-only."
        )
    return combined
