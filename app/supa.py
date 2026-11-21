"""Accès à Supabase AVEC le jeton de la personne connectée.

Le service n'a jamais la clé service_role : il lit les données avec le jeton de l'utilisateur, donc les règles de sécurité
(RLS) de la base s'appliquent. Le coach ne peut voir que les données de la personne qui lui parle.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from . import config


class AuthError(Exception):
    pass


class DataError(Exception):
    pass


@dataclass
class User:
    id: str
    token: str


_auth_cache: dict[str, tuple[float, str]] = {}  # jeton -> (expiration, user_id)


def _headers(token: str) -> dict[str, str]:
    return {"apikey": config.SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"}


async def authenticate(client: httpx.AsyncClient, authorization: str | None) -> User:
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        raise DataError("Service mal configuré : SUPABASE_URL ou SUPABASE_ANON_KEY manquant.")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Connexion requise.")
    token = authorization.split(" ", 1)[1].strip()
    cached = _auth_cache.get(token)
    if cached and cached[0] > time.time():
        return User(cached[1], token)
    r = await client.get(f"{config.SUPABASE_URL}/auth/v1/user", headers=_headers(token))
    if r.status_code != 200:
        raise AuthError("Session invalide ou expirée : reconnecte-toi dans l'app.")
    uid = r.json().get("id")
    if not uid:
        raise AuthError("Session invalide.")
    _auth_cache[token] = (time.time() + 60, uid)
    if len(_auth_cache) > 500:
        _auth_cache.clear()
    return User(uid, token)


async def select(client: httpx.AsyncClient, user: User, table: str, params: dict[str, str]) -> list[dict]:
    r = await client.get(f"{config.SUPABASE_URL}/rest/v1/{table}", params=params, headers=_headers(user.token))
    if r.status_code != 200:
        raise DataError(f"Lecture de {table} impossible ({r.status_code}) : {r.text[:200]}")
    return r.json()


async def insert(client: httpx.AsyncClient, user: User, table: str, rows: list[dict]) -> None:
    r = await client.post(
        f"{config.SUPABASE_URL}/rest/v1/{table}", json=rows,
        headers={**_headers(user.token), "Content-Type": "application/json", "Prefer": "return=minimal"},
    )
    if r.status_code not in (200, 201, 204):
        raise DataError(f"Écriture dans {table} impossible ({r.status_code}) : {r.text[:200]}")
