# Text chunking + document text extraction for the "Train Bot" admin
# feature — plan.txt section 4 update. Company policy documents are
# free-form long text, so RecursiveCharacterTextSplitter (not the
# structured per-record approach originally planned for product data).

import io

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def split_text(text: str) -> list[str]:
    return _splitter.split_text(text)


def extract_text_from_upload(filename: str, content: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext in ("txt", "md"):
        return content.decode("utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type: .{ext} (supported: .pdf, .txt, .md)")
