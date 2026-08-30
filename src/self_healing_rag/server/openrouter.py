"""Validate model ids against OpenRouter. Never log the API key."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from hashlib import sha256

from self_healing_rag.config import OPENROUTER_MODELS_URL

_TTL_SECONDS = 300
_cache: dict[str, tuple[float, set[str]]] = {}


def available_model_ids(api_key: str) -> set[str]:
    cache_key = sha256(api_key.encode("utf-8")).hexdigest()
    cached = _cache.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]

    request = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Could not list models from OpenRouter. Check the API key.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach OpenRouter to check model ids.") from exc

    ids = {
        str(item["id"]).strip()
        for item in payload.get("data") or []
        if isinstance(item, dict) and item.get("id")
    }
    if not ids:
        raise RuntimeError("OpenRouter returned an empty model list.")

    _cache[cache_key] = (time.time() + _TTL_SECONDS, ids)
    return ids


def unknown_models(api_key: str, model_ids: dict[str, str]) -> dict[str, str]:
    """Return {field: id} for ids that are not on OpenRouter."""
    catalog = available_model_ids(api_key)
    return {field: model_id for field, model_id in model_ids.items() if model_id not in catalog}
