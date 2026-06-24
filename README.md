# Resume Evaluator

A browser-friendly wrapper around **[HackerRank's Hiring Agent](https://github.com/interviewstreet/hiring-agent)** — an open-source resume-to-score pipeline originally built by [HackerRank](https://www.hackerrank.com/).

> **Attribution:** We did not build the core evaluation system. The scoring engine, prompts, PDF extraction, GitHub enrichment, and rubric come from [interviewstreet/hiring-agent](https://github.com/interviewstreet/hiring-agent) (MIT © HackerRank). This repository adds a **web UI** and small integration layer so you can upload a PDF and view results in the browser without using the CLI.

---

## What this repo adds

| Component | Description |
|-----------|-------------|
| [`web_app.py`](web_app.py) | FastAPI server with PDF upload endpoint |
| [`pipeline.py`](pipeline.py) | Wraps the upstream scoring pipeline for the web API |
| [`static/`](static/) | Simple drag-and-drop web interface |

Everything else (`score.py`, `evaluator.py`, `pdf.py`, `prompts/`, etc.) is from the upstream Hiring Agent project.

---

## How to use (Web UI)

### 1. Prerequisites

- **Python 3.11+**
- **An LLM backend** — either:
  - [Ollama](https://ollama.com/) (local, free) — run `ollama serve` and pull a model, e.g. `ollama pull gemma3:4b`
  - **Google Gemini** (cloud) — get an API key from [Google AI Studio](https://aistudio.google.com/apikey)

### 2. Install

```bash
git clone https://github.com/kunalagrawal2611/resume-evaluator.git
cd resume-evaluator

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Ollama (local)
LLM_PROVIDER=ollama
DEFAULT_MODEL=gemma3:4b

# Or Gemini (cloud)
# LLM_PROVIDER=gemini
# DEFAULT_MODEL=gemini-2.0-flash
# GEMINI_API_KEY=your_key_here
```

Optional: set `GITHUB_TOKEN` to avoid GitHub API rate limits when your resume includes a GitHub profile.

### 4. Start the web server

```bash
python -m uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** in your browser.

### 5. Evaluate a resume

1. Drag and drop a **PDF resume** onto the upload area (or click **Choose file**).
2. Wait while the system extracts sections, enriches GitHub data (if found), and scores the resume. The first run can take several minutes.
3. Review the results:
   - Overall score and category breakdown (Open Source, Self Projects, Production, Technical Skills)
   - Bonus points and deductions
   - Key strengths and areas for improvement

> **Windows tip:** If the CLI prints emoji errors, set `$env:PYTHONIOENCODING='utf-8'` before running commands.

---

## How to use (CLI — upstream)

The original command-line interface still works:

```bash
python score.py path/to/resume.pdf
```

With `DEVELOPMENT_MODE = True` in [`config.py`](config.py), results are cached under `cache/` and appended to `resume_evaluations.csv`.

---

## Configuration reference

| Variable | Values | Description |
|----------|--------|-------------|
| `LLM_PROVIDER` | `ollama` or `gemini` | LLM backend |
| `DEFAULT_MODEL` | e.g. `gemma3:4b`, `gemini-2.0-flash` | Model name |
| `GEMINI_API_KEY` | string | Required for Gemini |
| `GITHUB_TOKEN` | optional | Higher GitHub API rate limits |

---

## How the upstream system works

1. **PDF extraction** — PyMuPDF converts the resume to structured text.
2. **Section parsing** — An LLM extracts Basics, Work, Education, Skills, Projects, and Awards via Jinja prompts.
3. **GitHub enrichment** — If a GitHub URL is found, repos are fetched and ranked.
4. **Evaluation** — A rubric-based LLM scorer produces category scores with evidence, bonuses, and deductions.

See the [upstream README](https://github.com/interviewstreet/hiring-agent) and [Architecture docs](https://github.com/interviewstreet/hiring-agent#architecture) for full details.

---

## License

The core Hiring Agent code is **[MIT © HackerRank](https://github.com/interviewstreet/hiring-agent/blob/main/LICENSE)**.

Web UI additions in this repository are also released under the MIT License. Please retain upstream attribution when redistributing.
