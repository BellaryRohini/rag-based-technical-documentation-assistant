from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import DATA_DIR, CHROMA_DIR, MAX_RETRIES
from app.schemas import IngestRequest, QueryRequest, QueryResponse, SourceItem, FeedbackRequest
from app.ingestion import fetch_url, ingest_local_corpus, load_local_documents, rebuild_index
from app.graph import build_graph

load_dotenv()
app = FastAPI(
    title="Margin — Documentation Workspace",
    description="A local workspace for asking questions about technical documentation.",
    version="1.2.0",
)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
feedback_file = Path(__file__).resolve().parent.parent / "data" / "feedback.jsonl"
ALLOWED_EXTENSIONS = {".md", ".txt", ".html"}
MAX_UPLOAD_BYTES = 2_000_000


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "index_directory_exists": CHROMA_DIR.exists(), "max_retries": MAX_RETRIES}


def _validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {url}")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="URLs containing credentials are not allowed.")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="Local URLs are not allowed.")
    return url


def _index_documents(urls: list[str]) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    docs = load_local_documents()
    for url in urls:
        docs.append(fetch_url(_validate_public_http_url(url)))
    if not docs:
        raise HTTPException(status_code=400, detail="No documents found. Upload files or provide URLs.")
    chunks = rebuild_index(docs)
    return {"message": "Ingestion completed", "documents_loaded": len(docs), "chunks_indexed": chunks, "urls_fetched": len(urls)}


@app.post("/ingest", tags=["Ingestion"])
def ingest(request: IngestRequest):
    """Save public documentation pages into the local corpus and rebuild the index."""
    try:
        saved_urls = []
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for raw_url in request.urls:
            url = _validate_public_http_url(str(raw_url))
            document = fetch_url(url)
            title = str(document.metadata.get("document_id") or "documentation")
            slug = "".join(char.lower() if char.isalnum() else "-" for char in title).strip("-")
            slug = "-".join(part for part in slug.split("-") if part)[:55] or "documentation"
            import hashlib
            suffix = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
            filename = f"web-{slug}-{suffix}.md"
            content = f"# {title}\n\nSource: {url}\n\n{document.page_content}"
            (DATA_DIR / filename).write_text(content, encoding="utf-8")
            saved_urls.append(url)
        result = _index_documents([])
        result["urls_fetched"] = len(saved_urls)
        result["saved_web_pages"] = len(saved_urls)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@app.post("/ingest/files", tags=["Ingestion"])
async def ingest_files(files: list[UploadFile] = File(..., description="Markdown, text, or HTML files; max 2 MB each")):
    """Save uploaded files and rebuild the index from the local corpus."""
    saved_files: list[str] = []
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for upload in files:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported file type for {upload.filename}. Use .md, .txt, or .html.")
            content = await upload.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"File {upload.filename} is empty.")
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail=f"File {upload.filename} exceeds the 2 MB limit.")
            safe_name = Path(upload.filename or "upload.txt").name
            (DATA_DIR / safe_name).write_bytes(content)
            saved_files.append(safe_name)
        result = _index_documents([])
        result["uploaded_files"] = saved_files
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File ingestion failed: {exc}") from exc
    finally:
        for upload in files:
            await upload.close()


@app.post("/ingest/local", tags=["Ingestion"])
def ingest_local():
    """Re-index all Markdown, text, and HTML files already in data/documents."""
    try:
        count = ingest_local_corpus()
        return {"message": "Local corpus indexed", "chunks_indexed": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Local ingestion failed: {exc}") from exc


@app.get("/documents", tags=["Ingestion"])
def list_documents():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    documents = []
    for path in sorted(DATA_DIR.rglob("*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            documents.append({"name": path.name, "path": str(path.relative_to(DATA_DIR)), "bytes": path.stat().st_size, "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
    return {"count": len(documents), "documents": documents}


@app.post("/query", response_model=QueryResponse, tags=["RAG Query"])
def query(request: QueryRequest):
    try:
        result = build_graph().invoke({"question": request.question, "search_query": request.question, "retries": 0})
        sources = []
        seen = set()
        for doc in result.get("relevant_documents", []):
            source = str(doc.metadata.get("source", "unknown"))
            chunk_id = str(doc.metadata.get("chunk_id", ""))
            key = (source, chunk_id)
            if key in seen:
                continue
            seen.add(key)
            sources.append(SourceItem(source=source, chunk_id=chunk_id or None, preview=doc.page_content[:240].replace("\n", " ")))
        return QueryResponse(question=request.question, answer=result.get("answer", "No answer generated."), sources=sources, retries=result.get("retries", 0), status=result.get("status", "insufficient_context"))
    except Exception as exc:
        message = str(exc)
        status_code = 503 if "index does not exist" in message.lower() or "google_api_key" in message.lower() else 500
        raise HTTPException(status_code=status_code, detail=message) from exc


@app.post("/feedback", tags=["Feedback"])
def feedback(request: FeedbackRequest):
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    record = request.model_dump()
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    with feedback_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"message": "Feedback saved", "rating": request.rating}


@app.get("/feedback", tags=["Feedback"])
def feedback_summary():
    if not feedback_file.exists():
        return {"count": 0, "feedback": []}
    records = []
    for line in feedback_file.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"count": len(records), "feedback": records}
