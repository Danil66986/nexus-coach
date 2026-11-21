"""NEXUS COACH : API du coach. Lance avec : uvicorn app.main:app --host 0.0.0.0 --port 7860"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import config, context as cx, llm, prompts, rules, supa

log = logging.getLogger("coach")
logging.basicConfig(level=logging.INFO)

# Réponses calculées avec tes vraies données : on les garde pour les questions factuelles (exactes et gratuites).
ALWAYS_RULES = {"pain", "sick", "ride"}                       # jamais confiés à l'IA
SHORT_RULES = {"today", "tomorrow", "week", "zones", "help"}  # calculés si la question est courte


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=25)
    yield
    await app.state.http.aclose()


app = FastAPI(title="NEXUS COACH", lifespan=lifespan)
# Pas de cookies : l'accès est protégé par le jeton Supabase de chaque personne, donc on accepte toutes les origines.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_hits: dict[str, deque] = defaultdict(deque)


def _check_rate(uid: str) -> None:
    now, q = time.time(), _hits[uid]
    while q and q[0] < now - config.RATE_LIMIT_WINDOW_S:
        q.popleft()
    if len(q) >= config.RATE_LIMIT_MESSAGES:
        raise HTTPException(429, "Tu m'envoies beaucoup de messages. Réessaie dans quelques minutes.")
    q.append(now)


async def _user(authorization: str | None) -> supa.User:
    try:
        return await supa.authenticate(app.state.http, authorization)
    except supa.AuthError as e:
        raise HTTPException(401, str(e))
    except supa.DataError as e:
        raise HTTPException(500, str(e))


async def _context(user: supa.User) -> dict:
    try:
        return await cx.load_context(app.state.http, user)
    except supa.DataError as e:
        log.warning("lecture des données: %s", e)
        raise HTTPException(502, "Je n'arrive pas à lire tes données pour l'instant. Réessaie dans un instant.")
    except httpx.HTTPError as e:
        log.warning("réseau: %s", e)
        raise HTTPException(502, "Je n'arrive pas à joindre ta base de données. Réessaie dans un instant.")


async def _save(user: supa.User, rows: list[dict]) -> None:
    try:
        # PostgREST exige que toutes les lignes d'un même envoi aient exactement les mêmes champs
        await supa.insert(app.state.http, user, "coach_messages",
                          [{"user_id": user.id, "role": r["role"], "content": r["content"], "source": r.get("source")} for r in rows])
    except (supa.DataError, httpx.HTTPError) as e:
        log.warning("sauvegarde de la conversation: %s", e)  # la réponse reste valable même si l'historique échoue


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatOut(BaseModel):
    reply: str
    source: str
    intent: str


@app.get("/health")
async def health():
    return {"ok": True, "llm": config.llm_provider()}


@app.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn, authorization: str | None = Header(default=None)):
    user = await _user(authorization)
    _check_rate(user.id)
    message = body.message.strip()
    ctx = await _context(user)
    rule_reply, intent = rules.answer(message, ctx)
    reply, source = rule_reply, "rules"

    # Réponse « calculée » (exacte, gratuite) quand la question est une demande de données courte ; sécurité et préparation de sortie
    # restent toujours calculées. Une phrase libre ou longue va à l'IA, qui s'appuie sur les chiffres exacts du coach.
    deterministic = intent in ALWAYS_RULES or (intent in SHORT_RULES and len(message.split()) <= 6)
    if config.llm_provider() != "none" and not deterministic:
        try:
            history = await supa.select(app.state.http, user, "coach_messages", {
                "user_id": f"eq.{user.id}", "select": "role,content", "order": "created_at.desc", "limit": "8"})
            history.reverse()
            facts = f"\n\n[Données exactes calculées pour cette question, à utiliser telles quelles]\n{rule_reply}" if intent not in ("fallback",) else ""
            reply = await llm.ask(app.state.http, prompts.system_prompt(ctx), history, message + facts)
            source = "llm"
        except (llm.LLMError, supa.DataError, httpx.HTTPError) as e:
            log.warning("IA indisponible, repli sur les règles: %s", e)

    await _save(user, [{"role": "user", "content": message}, {"role": "assistant", "content": reply, "source": source}])
    return ChatOut(reply=reply, source=source, intent=intent)


@app.get("/brief", response_model=ChatOut)
async def brief(save: bool = True, authorization: str | None = Header(default=None)):
    user = await _user(authorization)
    ctx = await _context(user)
    text = rules.brief(ctx)
    if save:
        await _save(user, [{"role": "assistant", "content": text, "source": "rules"}])
    return ChatOut(reply=text, source="rules", intent="brief")


@app.get("/context")
async def what_i_know(authorization: str | None = Header(default=None)):
    """Ce que le coach sait de toi (résumé chiffré) : pratique pour vérifier que tout est bien branché."""
    user = await _user(authorization)
    ctx = await _context(user)
    pos = cx.plan_position(ctx)
    return {
        "onboarding_done": ctx["onboarding_done"],
        "limitation_signalee": ctx["restrict_intense"],
        "fc_max": ctx["max_hr"], "fc_repos": ctx["rest_hr"],
        "plan": pos["name"] if pos else None,
        "seances_dans_le_plan": len(ctx["workouts"]),
        "sorties_200_jours": len(ctx["rides"]),
        "mesures": len(ctx["measurements"]),
        "forme": {k: round(ctx["load"][k]) for k in ("ctl", "atl", "tsb")},
        "ia": config.llm_provider(),
    }
