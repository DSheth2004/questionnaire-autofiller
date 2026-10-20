"""HTTP API for the React frontend (and it serves the built frontend too).

Run:  python -m uvicorn server:app --port 8000
Then open http://localhost:8000 (uses the pre-built frontend in web/dist), or run the Vite dev server
in web/ for live reloading.
"""
import io
import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from autofill.answer import ABSTAIN_STRENGTH, draft_answer
from autofill.fill import build_retriever
from autofill.llm import get_llm
from autofill.questionnaire import read_xlsx, write_answers_xlsx

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "data" / "samples" / "vsaq_questionnaire.xlsx"
DIST = ROOT / "web" / "dist"
MODES = {
    "bm25+expand": "Keyword + compliance synonyms",
    "bm25": "Keyword only",
    "hybrid": "Hybrid (keyword + embeddings)",
    "dense": "Embeddings only",
}

app = FastAPI(title="Questionnaire Auto-Filler")


@lru_cache(maxsize=4)
def retriever(mode: str):
    if mode not in MODES:
        raise HTTPException(400, f"Unknown search method {mode!r}")
    try:
        return build_retriever(mode)
    except Exception as e:  # embedding model missing or offline
        raise HTTPException(400, f"{MODES[mode]} isn't available: {e}") from None


def read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


@app.get("/api/info")
def info():
    r = retriever("bm25+expand")
    llm = get_llm()
    docs = sorted({(c.title, c.url) for c in r.chunks})
    return {
        "documents": [{"title": t, "url": u, "sections": sum(1 for c in r.chunks if c.url == u)} for t, u in docs],
        "chunks": len(r.chunks),
        "providers": [{"name": p.name, "model": p.model} for p in llm.providers] if llm else [],
        "modes": [{"id": k, "label": v} for k, v in MODES.items()],
        "eval": read_json(ROOT / "eval" / "results.json"),
        "abstention": read_json(ROOT / "eval" / "abstention.json"),
        "abstain_threshold": ABSTAIN_STRENGTH,
        "sample_questions": len(read_xlsx(SAMPLE)),
    }


class AskRequest(BaseModel):
    question: str
    mode: str = "bm25+expand"


@app.post("/api/ask")
def ask(req: AskRequest):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "Question is empty")
    r = retriever(req.mode)
    hits = r.search(q, k=5)
    best = max(s for _, s in hits) or 1
    return {
        "result": draft_answer(q, r),
        "hits": [{"title": c.title, "section": c.section, "url": c.url, "text": c.text,
                  "score": round(s / best, 3)} for c, s in hits],
    }


@app.post("/api/fill")
async def fill_questionnaire(file: UploadFile | None = File(None), mode: str = Form("bm25+expand")):
    """Streams one JSON line per answered question so the UI can show live progress."""
    try:
        questions = read_xlsx(io.BytesIO(await file.read()) if file else SAMPLE)
    except Exception as e:
        raise HTTPException(400, f"Couldn't read that file: {e}") from None
    r = retriever(mode)

    def stream():
        yield json.dumps({"type": "start", "total": len(questions)}) + "\n"
        for i, q in enumerate(questions):
            row = {"id": q["id"], "section": q["section"], **draft_answer(q["question"], r)}
            yield json.dumps({"type": "row", "index": i, "row": row}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


class ExportRequest(BaseModel):
    results: list[dict]


@app.post("/api/export")
def export(req: ExportRequest):
    buf = io.BytesIO()
    write_answers_xlsx(req.results, buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="answers.xlsx"'})


@app.get("/api/sample")
def sample():
    return FileResponse(SAMPLE, filename="vsaq_questionnaire.xlsx")


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
