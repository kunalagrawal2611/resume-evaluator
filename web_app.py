"""FastAPI web UI for resume evaluation."""

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import evaluate_resume_pdf
from prompt import DEFAULT_MODEL

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Resume Checker", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": DEFAULT_MODEL}


@app.post("/api/evaluate")
async def evaluate(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    pdf_path = upload_dir / safe_name

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File must be under 10 MB.")

        pdf_path.write_bytes(contents)
        result = evaluate_resume_pdf(str(pdf_path))
        result["filename"] = file.filename
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if pdf_path.exists():
            try:
                pdf_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)
