"""Read and write local .env settings for the web UI."""

import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from models import ModelProvider
from prompt import coerce_model_for_provider
from llm_utils import is_valid_gemini_api_key_format, normalize_gemini_api_key, validate_gemini_api_key

ENV_PATH = Path(__file__).parent / ".env"


def _parse_env_lines() -> list[str]:
    if not ENV_PATH.exists():
        return []
    return ENV_PATH.read_text(encoding="utf-8").splitlines()


def _upsert_env_line(lines: list[str], key: str, value: str) -> list[str]:
    pattern = re.compile(rf"^{re.escape(key)}=")
    new_line = f"{key}={value}"
    updated = False
    result: list[str] = []

    for line in lines:
        if pattern.match(line):
            result.append(new_line)
            updated = True
        else:
            result.append(line)

    if not updated:
        if result and result[-1].strip():
            result.append("")
        result.append(new_line)

    return result


def read_settings() -> dict:
    load_dotenv(ENV_PATH, override=True)
    provider = os.getenv("LLM_PROVIDER", "ollama")
    default_model = coerce_model_for_provider(
        provider, os.getenv("DEFAULT_MODEL", "gemma3:4b")
    )
    api_key = os.getenv("GEMINI_API_KEY", "")

    return {
        "llm_provider": provider,
        "default_model": default_model,
        "gemini_api_key_set": bool(api_key.strip()),
        "gemini_api_key_valid": is_valid_gemini_api_key_format(api_key) if api_key.strip() else False,
        "gemini_api_key_preview": _mask_key(api_key),
    }


def _mask_key(key: str) -> str:
    key = key.strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "********"
    return f"{key[:4]}...{key[-4:]}"


def write_settings(
    *,
    llm_provider: str,
    default_model: str,
    gemini_api_key: Optional[str] = None,
    clear_gemini_api_key: bool = False,
) -> dict:
    default_model = coerce_model_for_provider(llm_provider, default_model)
    lines = _parse_env_lines()
    lines = _upsert_env_line(lines, "LLM_PROVIDER", llm_provider)
    lines = _upsert_env_line(lines, "DEFAULT_MODEL", default_model)

    if clear_gemini_api_key:
        lines = _upsert_env_line(lines, "GEMINI_API_KEY", "")
    elif gemini_api_key is not None and gemini_api_key.strip():
        normalized_key = normalize_gemini_api_key(gemini_api_key)
        validate_gemini_api_key(normalized_key)
        lines = _upsert_env_line(lines, "GEMINI_API_KEY", normalized_key)

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    apply_runtime_settings()
    return read_settings()


def apply_evaluation_settings(
    *,
    provider: str,
    model_name: str,
    gemini_api_key: str = "",
    persist: bool = True,
) -> None:
    """Apply provider/model/key for a single evaluation request."""
    load_dotenv(ENV_PATH, override=True)

    provider = provider or os.getenv("LLM_PROVIDER", ModelProvider.OLLAMA.value)
    model_name = coerce_model_for_provider(
        provider, model_name or os.getenv("DEFAULT_MODEL", "gemma3:4b")
    )

    if provider == ModelProvider.GEMINI.value:
        key = normalize_gemini_api_key(
            gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        )
        validate_gemini_api_key(key)
        if persist and normalize_gemini_api_key(gemini_api_key):
            write_settings(
                llm_provider="gemini",
                default_model=model_name,
                gemini_api_key=key,
            )
            return

        import prompt

        prompt.PROVIDER = provider
        prompt.DEFAULT_MODEL = model_name
        prompt.GEMINI_API_KEY = key
        return

    if persist:
        write_settings(
            llm_provider="ollama",
            default_model=model_name,
            gemini_api_key=None,
        )
        return

    import prompt

    prompt.PROVIDER = provider
    prompt.DEFAULT_MODEL = model_name


def apply_runtime_settings() -> None:
    """Reload environment variables into the running process."""
    load_dotenv(ENV_PATH, override=True)

    import prompt

    prompt.PROVIDER = os.getenv("LLM_PROVIDER", prompt.DEFAULT_PROVIDER.value)
    prompt.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    if prompt.PROVIDER not in [p.value for p in ModelProvider]:
        prompt.PROVIDER = prompt.DEFAULT_PROVIDER.value

    prompt.DEFAULT_MODEL = coerce_model_for_provider(
        prompt.PROVIDER,
        os.getenv("DEFAULT_MODEL", prompt.DEFAULT_MODEL_NAME),
    )
