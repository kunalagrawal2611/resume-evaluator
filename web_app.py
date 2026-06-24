"""FastAPI web UI for resume evaluation."""

import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline import evaluate_resume_pdf
from prompt import DEFAULT_MODEL, list_available_models
from settings_manager import apply_evaluation_settings, apply_runtime_settings, read_settings, write_settings
from llm_utils import LLMRequestError, validate_gemini_api_key

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Resume Checker", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

apply_runtime_settings()


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    settings = read_settings()
    return {
        "status": "ok",
        "provider": settings["llm_provider"],
        "model": settings["default_model"],
        "gemini_key_valid": settings.get("gemini_api_key_valid", False),
        "api_version": 2,
    }


@app.get("/api/settings")
async def get_settings():
    return read_settings()


class SettingsUpdate(BaseModel):
    llm_provider: str = Field(pattern="^(ollama|gemini)$")
    default_model: str = Field(min_length=1)
    gemini_api_key: str = ""
    clear_gemini_api_key: bool = False


@app.post("/api/settings")
async def update_settings(body: SettingsUpdate):
    try:
        if body.llm_provider == "gemini" and body.gemini_api_key.strip():
            validate_gemini_api_key(body.gemini_api_key)
        elif body.llm_provider == "gemini" and not body.gemini_api_key.strip():
            current = read_settings()
            if not current["gemini_api_key_set"] and not body.clear_gemini_api_key:
                raise HTTPException(
                    status_code=400,
                    detail="Gemini API key is required when using the Gemini provider.",
                )

        return write_settings(
            llm_provider=body.llm_provider,
            default_model=body.default_model,
            gemini_api_key=body.gemini_api_key,
            clear_gemini_api_key=body.clear_gemini_api_key,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/models")
async def models(provider: str = "ollama"):
    apply_runtime_settings()
    return list_available_models(provider=provider)


@app.post("/api/evaluate")
async def evaluate(
    file: UploadFile = File(...),
    model: str = Form(default=""),
    provider: str = Form(default=""),
    gemini_api_key: str = Form(default=""),
):
    try:
        apply_evaluation_settings(
            provider=provider.strip() or read_settings()["llm_provider"],
            model_name=model.strip(),
            gemini_api_key=gemini_api_key.strip(),
            persist=bool(gemini_api_key.strip()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    import prompt

    model_name = prompt.DEFAULT_MODEL

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
        result = evaluate_resume_pdf(str(pdf_path), model_name=model_name)
        result["filename"] = file.filename
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMRequestError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
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
