"""Réglages, lus dans les variables d'environnement (jamais écrits dans le code)."""
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Fuseau des dates (séances du plan, sorties). Le serveur tourne en UTC : sans ça, une sortie de 23 h serait décalée d'un jour.
TZ = ZoneInfo(os.environ.get("COACH_TZ", "Europe/Paris"))

# IA optionnelle. none = le coach répond avec ses règles expertes, sans qu'aucune donnée ne quitte ton service.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")  # compatible OpenAI (Groq, OpenRouter, ...)
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")


def llm_provider() -> str:
    forced = os.environ.get("COACH_LLM", "").lower()
    if forced in ("none", "gemini", "openai"):
        return forced
    if GEMINI_API_KEY:
        return "gemini"
    if LLM_API_KEY and LLM_BASE_URL and LLM_MODEL:
        return "openai"
    return "none"


def today() -> date:
    return datetime.now(TZ).date()


RATE_LIMIT_MESSAGES = int(os.environ.get("COACH_RATE_LIMIT", "30"))  # messages par fenêtre et par personne
RATE_LIMIT_WINDOW_S = int(os.environ.get("COACH_RATE_WINDOW", "600"))
