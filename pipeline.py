"""Reusable resume evaluation pipeline for CLI and web UI."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config import DEVELOPMENT_MODE
from github import fetch_and_display_github_info
from models import EvaluationData, JSONResume
from pdf import PDFHandler
from score import _evaluate_resume, find_profile, is_valid_resume_data

CATEGORY_LABELS = {
    "open_source": "Open Source",
    "self_projects": "Self Projects",
    "production": "Production Experience",
    "technical_skills": "Technical Skills",
}


def _compute_totals(evaluation: EvaluationData) -> tuple[float, float, float]:
    """Return (category_total, category_max, final_score with bonus/deductions)."""
    total_score = 0.0
    max_score = 0.0

    if evaluation.scores:
        for category_data in evaluation.scores.model_dump().values():
            capped = min(category_data["score"], category_data["max"])
            total_score += capped
            max_score += category_data["max"]

    final_score = total_score
    if evaluation.bonus_points:
        final_score += evaluation.bonus_points.total
    if evaluation.deductions:
        final_score -= evaluation.deductions.total

    max_possible = max_score + 20
    if final_score > max_possible:
        final_score = max_possible

    return total_score, max_score, final_score


def evaluation_to_response(
    evaluation: EvaluationData,
    candidate_name: str,
    resume_data: Optional[JSONResume] = None,
    *,
    from_cache: bool = False,
) -> Dict[str, Any]:
    """Convert evaluation models into a JSON-serializable API response."""
    category_total, category_max, final_score = _compute_totals(evaluation)

    categories = []
    if evaluation.scores:
        for key, cat_label in CATEGORY_LABELS.items():
            item = getattr(evaluation.scores, key, None)
            if item:
                categories.append(
                    {
                        "key": key,
                        "label": cat_label,
                        "score": min(item.score, item.max),
                        "max": item.max,
                        "evidence": item.evidence,
                    }
                )

    basics = None
    if resume_data and resume_data.basics:
        basics = {
            "name": resume_data.basics.name,
            "email": resume_data.basics.email,
            "summary": resume_data.basics.summary,
        }

    return {
        "candidate_name": candidate_name,
        "from_cache": from_cache,
        "basics": basics,
        "overall": {
            "final_score": round(final_score, 1),
            "category_total": round(category_total, 1),
            "category_max": category_max,
        },
        "categories": categories,
        "bonus_points": evaluation.bonus_points.model_dump()
        if evaluation.bonus_points
        else None,
        "deductions": evaluation.deductions.model_dump()
        if evaluation.deductions
        else None,
        "key_strengths": evaluation.key_strengths,
        "areas_for_improvement": evaluation.areas_for_improvement,
    }


def extract_resume_from_pdf(pdf_path: str) -> Tuple[JSONResume, bool]:
    """Extract structured resume data from a PDF, using cache when available."""
    basename = os.path.basename(pdf_path).replace(".pdf", "")
    cache_filename = f"cache/resumecache_{basename}.json"
    from_cache = False

    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            loaded_resume = JSONResume(**cached_data)
            if not is_valid_resume_data(loaded_resume):
                raise ValueError("Cached resume data contains no core content")
            return loaded_resume, True
        except Exception:
            try:
                os.remove(cache_filename)
            except OSError:
                pass

    pdf_handler = PDFHandler()
    resume_data = pdf_handler.extract_json_from_pdf(pdf_path)
    if resume_data is None:
        raise ValueError("Failed to extract data from the PDF.")

    if DEVELOPMENT_MODE and is_valid_resume_data(resume_data):
        os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
        Path(cache_filename).write_text(
            json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return resume_data, from_cache


def fetch_github_for_resume(
    resume_data: JSONResume, pdf_path: Optional[str] = None
) -> dict:
    """Fetch GitHub enrichment data for a resume, using cache when available."""
    basename = (
        os.path.basename(pdf_path).replace(".pdf", "")
        if pdf_path
        else (resume_data.basics.name or "resume").replace(" ", "_")
    )
    github_cache_filename = f"cache/githubcache_{basename}.json"

    if DEVELOPMENT_MODE and os.path.exists(github_cache_filename):
        try:
            loaded_github = json.loads(
                Path(github_cache_filename).read_text(encoding="utf-8")
            )
            if (
                isinstance(loaded_github, dict)
                and loaded_github
                and "profile" in loaded_github
            ):
                return loaded_github
        except Exception:
            try:
                os.remove(github_cache_filename)
            except OSError:
                pass

    github_data: dict = {}
    profiles = resume_data.basics.profiles or [] if resume_data.basics else []
    github_profile = find_profile(profiles, "Github")

    if github_profile:
        github_data = fetch_and_display_github_info(github_profile.url) or {}
        if (
            DEVELOPMENT_MODE
            and github_data
            and isinstance(github_data, dict)
            and "profile" in github_data
        ):
            os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
            Path(github_cache_filename).write_text(
                json.dumps(github_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    return github_data


def evaluate_resume_data(
    resume_data: JSONResume,
    github_data: Optional[dict] = None,
    *,
    from_cache: bool = False,
) -> Dict[str, Any]:
    """Evaluate structured resume data and return API response."""
    evaluation = _evaluate_resume(resume_data, github_data or {})
    if evaluation is None:
        raise ValueError("Evaluation failed to produce results.")

    candidate_name = "Candidate"
    if resume_data.basics and resume_data.basics.name:
        candidate_name = resume_data.basics.name

    return evaluation_to_response(
        evaluation,
        candidate_name,
        resume_data,
        from_cache=from_cache,
    )


def evaluate_resume_pdf(pdf_path: str) -> Dict[str, Any]:
    """Run the full resume-to-score pipeline from a PDF path."""
    resume_data, from_cache = extract_resume_from_pdf(pdf_path)
    github_data = fetch_github_for_resume(resume_data, pdf_path)
    return evaluate_resume_data(resume_data, github_data, from_cache=from_cache)
