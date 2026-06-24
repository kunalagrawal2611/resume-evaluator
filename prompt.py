"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

import os
from dotenv import load_dotenv
from models import ModelProvider

# Load environment variables
load_dotenv()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"
DEFAULT_PROVIDER = ModelProvider.OLLAMA

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Validate provider
if PROVIDER not in [p.value for p in ModelProvider]:
    PROVIDER = DEFAULT_PROVIDER.value

# Model-specific parameters
MODEL_PARAMETERS = {
    # Ollama models
    "qwen3:1.7b": {"temperature": 0.0, "top_p": 0.9},
    "gemma3:1b": {"temperature": 0.0, "top_p": 0.9},
    "qwen3:4b": {"temperature": 0.1, "top_p": 0.4},
    "gemma3:4b": {"temperature": 0.1, "top_p": 0.9},
    "gemma3:12b": {"temperature": 0.1, "top_p": 0.9},
    "mistral:7b": {"temperature": 0.1, "top_p": 0.9},
    # Google Gemini models
    "gemini-2.0-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.0-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-pro": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.1-flash-lite": {"temperature": 0.1, "top_p": 0.9},
}

# Model provider mapping
# Maps model names to their provider
MODEL_PROVIDER_MAPPING = {
    # Ollama models
    "qwen3:1.7b": ModelProvider.OLLAMA,
    "gemma3:1b": ModelProvider.OLLAMA,
    "qwen3:4b": ModelProvider.OLLAMA,
    "gemma3:4b": ModelProvider.OLLAMA,
    "gemma3:12b": ModelProvider.OLLAMA,
    "mistral:7b": ModelProvider.OLLAMA,
    # Google Gemini models
    "gemini-2.0-flash": ModelProvider.GEMINI,
    "gemini-2.0-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-flash": ModelProvider.GEMINI,
    "gemini-2.5-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-pro": ModelProvider.GEMINI,
    "gemini-3.5-flash": ModelProvider.GEMINI,
    "gemini-3.1-flash-lite": ModelProvider.GEMINI,
}

# Ordered list for the Gemini model dropdown in the web UI.
GEMINI_MODEL_OPTIONS = [
    ("gemini-2.5-flash", "Gemini 2.5 Flash (recommended)"),
    ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro"),
    ("gemini-2.0-flash", "Gemini 2.0 Flash"),
    ("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite"),
    ("gemini-3.5-flash", "Gemini 3.5 Flash"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite"),
]

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def is_gemini_model(model_name: str) -> bool:
    return model_name.strip().lower().startswith("gemini")


def coerce_model_for_provider(provider: str, model_name: str) -> str:
    """Return a model name that matches the selected provider."""
    provider = (provider or DEFAULT_PROVIDER.value).lower()
    model_name = (model_name or "").strip()

    if provider == ModelProvider.GEMINI.value:
        return model_name if is_gemini_model(model_name) else DEFAULT_GEMINI_MODEL_NAME

    if is_gemini_model(model_name):
        return DEFAULT_MODEL_NAME

    return model_name or DEFAULT_MODEL_NAME


def list_ollama_models() -> list[dict]:
    """Return only models reported by `ollama list` on this machine."""
    import subprocess

    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []

    if result.returncode != 0:
        return []

    models: list[dict] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("NAME"):
            continue
        name = line.split()[0]
        if name:
            models.append(
                {
                    "id": name,
                    "label": name,
                    "provider": ModelProvider.OLLAMA.value,
                }
            )
    return models


def list_gemini_models() -> list[dict]:
    """Return supported Gemini models for the web UI dropdown."""
    return [
        {
            "id": model_id,
            "label": label,
            "provider": ModelProvider.GEMINI.value,
        }
        for model_id, label in GEMINI_MODEL_OPTIONS
        if MODEL_PROVIDER_MAPPING.get(model_id) == ModelProvider.GEMINI
    ]


def list_available_models(provider: str | None = None) -> dict:
    """Return models for the UI based on provider and this machine's setup."""
    active_provider = (provider or PROVIDER or ModelProvider.OLLAMA.value).lower()

    if active_provider == ModelProvider.GEMINI.value:
        models = list_gemini_models()
        default = coerce_model_for_provider(
            active_provider,
            DEFAULT_MODEL if DEFAULT_MODEL in {m["id"] for m in models} else "",
        )
        return {"default": default, "models": models, "provider": active_provider}

    models = list_ollama_models()
    installed_ids = {model["id"] for model in models}
    default = DEFAULT_MODEL if DEFAULT_MODEL in installed_ids else (
        models[0]["id"] if models else ""
    )
    return {"default": default, "models": models, "provider": ModelProvider.OLLAMA.value}
