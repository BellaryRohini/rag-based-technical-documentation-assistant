from pathlib import Path
import hashlib
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from app.config import (
    DATA_DIR, CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP
)

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def load_local_documents() -> list[Document]:
    docs = []
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(DATA_DIR.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".html"}:
            raw = path.read_text(encoding="utf-8", errors="ignore")
            if path.suffix.lower() == ".html":
                raw = BeautifulSoup(raw, "html.parser").get_text("\n")
            if raw.strip():
                docs.append(Document(
                    page_content=raw,
                    metadata={"source": str(path.relative_to(DATA_DIR)), "document_id": path.name}
                ))
    return docs

def fetch_url(url: str) -> Document:
    response = requests.get(url, timeout=20, headers={"User-Agent": "DocumentationAssistant/1.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    content = soup.get_text("\n", strip=True)
    return Document(page_content=content, metadata={"source": url, "document_id": title})

def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        identity = f'{chunk.metadata.get("source", "doc")}:{i}:{chunk.page_content}'.encode("utf-8")
        digest = hashlib.sha1(identity).hexdigest()[:10]
        chunk.metadata["chunk_id"] = f'{chunk.metadata.get("document_id", "doc")}-{i}-{digest}'
    return chunks

def rebuild_index(documents: list[Document]) -> int:
    chunks = split_documents(documents)
    if not chunks:
        raise ValueError("No readable document content was found.")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    # Recreate the collection from the provided corpus to avoid stale/duplicate chunks.
    try:
        existing = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=str(CHROMA_DIR),
            embedding_function=get_embeddings()
        )
        existing.delete_collection()
    except Exception:
        pass
    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR)
    )
    return len(chunks)

def ingest_local_corpus() -> int:
    docs = load_local_documents()
    if not docs:
        raise ValueError(f"No .md, .txt, or .html files found in {DATA_DIR}")
    return rebuild_index(docs)

def get_vector_store():
    if not CHROMA_DIR.exists():
        raise RuntimeError(
            "The document index does not exist yet. "
            "Open Add documents and select Rebuild library."
        )

    try:
        store = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=str(CHROMA_DIR),
            embedding_function=get_embeddings()
        )

        if store._collection.count() == 0:
            raise RuntimeError(
                "The document index is empty. "
                "Add documents and rebuild the library."
            )

        return store

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "The document index is missing or incomplete. "
            "Rebuild the library and try again."
        ) from exc
