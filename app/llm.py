"""Connecteurs d'IA optionnels. Tous renvoient simplement du texte. En cas d'erreur, le coach retombe sur ses règles."""
from __future__ import annotations

import httpx

from . import config


class LLMError(Exception):
    pass


async def ask(client: httpx.AsyncClient, system: str, history: list[dict], message: str) -> str:
    provider = config.llm_provider()
    if provider == "gemini":
        return await _gemini(client, system, history, message)
    if provider == "openai":
        return await _openai(client, system, history, message)
    raise LLMError("Aucune IA configurée.")


async def _gemini(client: httpx.AsyncClient, system: str, history: list[dict], message: str) -> str:
    contents = [{"role": "user" if h["role"] == "user" else "model", "parts": [{"text": h["content"]}]} for h in history]
    contents.append({"role": "user", "parts": [{"text": message}]})
    r = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.6, "maxOutputTokens": 1200,
                # Les modèles 2.5 « réfléchissent » avec des jetons comptés dans la limite de sortie : sans ça, la réponse peut être coupée ou vide.
                **({"thinkingConfig": {"thinkingBudget": 0}} if "2.5" in config.GEMINI_MODEL and "pro" not in config.GEMINI_MODEL else {}),
            },
        },
        timeout=40,
    )
    if r.status_code != 200:
        raise LLMError(f"Gemini {r.status_code}: {r.text[:200]}")
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Réponse Gemini inattendue : {e}") from e
    if not text:
        raise LLMError("Réponse Gemini vide.")
    return text


async def _openai(client: httpx.AsyncClient, system: str, history: list[dict], message: str) -> str:
    msgs = [{"role": "system", "content": system}]
    msgs += [{"role": h["role"], "content": h["content"]} for h in history]
    msgs.append({"role": "user", "content": message})
    r = await client.post(
        f"{config.LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"},
        json={"model": config.LLM_MODEL, "messages": msgs, "temperature": 0.6, "max_tokens": 800},
        timeout=40,
    )
    if r.status_code != 200:
        raise LLMError(f"LLM {r.status_code}: {r.text[:200]}")
    try:
        text = r.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Réponse LLM inattendue : {e}") from e
    if not text:
        raise LLMError("Réponse LLM vide.")
    return text
