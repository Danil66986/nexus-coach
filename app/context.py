"""Construit le « dossier » du coach : tout ce qu'il sait de toi, tiré de ta base de données."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import httpx

from . import config, fitness, supa

BLOCK_ZONE_NAMES = {1: "zone 1", 2: "zone 2", 3: "zone 3", 4: "zone 4", 5: "zone 5"}


async def load_context(client: httpx.AsyncClient, user: supa.User) -> dict[str, Any]:
    uid = f"eq.{user.id}"
    since = (config.today() - timedelta(days=200)).isoformat()
    plan_since = (config.today() - timedelta(days=21)).isoformat()
    (coach, prof, plans, rides, meas) = await asyncio.gather(
        supa.select(client, user, "coach_profiles", {"user_id": uid, "select": "status,profile,restrict_intense,updated_at"}),
        supa.select(client, user, "profiles", {"id": uid, "select": "name,max_hr,rest_hr,hr_auto,strava_athlete_id"}),
        supa.select(client, user, "training_plans", {"user_id": uid, "active": "eq.true", "select": "*", "order": "created_at.desc", "limit": "1"}),
        supa.select(client, user, "rides", {  # les sorties sont lisibles par les deux comptes : on filtre sur toi
            "user_id": uid, "started_at": f"gte.{since}", "select": "title,started_at,duration_min,distance_km,elevation_m,avg_hr,max_hr_ride",
            "order": "started_at.desc", "limit": "600"}),
        supa.select(client, user, "measurements", {"user_id": uid, "select": "kind,value,measured_at", "order": "measured_at.desc", "limit": "60"}),
    )
    plan = plans[0] if plans else None
    # Toutes tes séances, comme l'onglet Plan : celles du plan actif ET celles ajoutées à la main.
    workouts = await supa.select(client, user, "workouts", {
        "user_id": uid, "date": f"gte.{plan_since}",
        "select": "date,title,blocks,done,kind,week_no,phase,notes,plan_id", "order": "date.asc", "limit": "400"})
    if plan:  # une séance d'un ancien plan n'est plus d'actualité
        workouts = [w for w in workouts if w.get("plan_id") in (None, plan["id"])]

    p = prof[0] if prof else {}
    profile_doc = (coach[0].get("profile") if coach else None) or {}
    max_hr = float(p.get("max_hr") or 190)
    rest_hr = float(p.get("rest_hr") or 60)
    load = fitness.compute_load(rides, max_hr, rest_hr)

    return {
        "today": config.today(),
        "profile": p,
        "coach_profile": profile_doc,
        "restrict_intense": bool(coach[0].get("restrict_intense")) if coach else False,
        "onboarding_done": bool(coach and coach[0].get("status") == "completed"),
        "max_hr": max_hr,
        "rest_hr": rest_hr,
        "plan": plan,
        "workouts": workouts,
        "rides": rides,
        "measurements": meas,
        "load": load,
    }


# ---------- aides de lecture du dossier ----------
def workout_on(ctx: dict, d: date) -> dict | None:
    iso = d.isoformat()
    sel = [w for w in ctx["workouts"] if w["date"] == iso]
    return sel[0] if sel else None


def plan_position(ctx: dict) -> dict | None:
    plan = ctx.get("plan")
    if not plan:
        return None
    start = date.fromisoformat(plan["start_date"])
    today = ctx["today"]
    week = (today - start).days // 7 + 1
    phases = (plan.get("meta") or {}).get("phases") or []
    started = today >= start
    week_c = min(max(week, 1), plan["weeks"])
    goal = date.fromisoformat(plan["goal_date"]) if plan.get("goal_date") else None
    return {
        "name": plan["name"], "weeks": plan["weeks"], "started": started, "week": week_c,
        "phase": phases[week_c - 1] if 0 < week_c <= len(phases) else None,
        "days_to_goal": (goal - today).days if goal else None,
        "start": start,
    }


def describe_blocks(blocks: list[dict], max_hr: float, rest_hr: float) -> list[str]:
    lines = []
    for b in blocks or []:
        m = float(b["minutes"])
        dur = f"{round(m * 60)} s" if m < 1 else f"{m:g} min"
        reps = f"{b['reps']}× " if b.get("reps") else ""
        lo, hi = fitness.zone_bounds(max_hr, rest_hr, int(b["zone"]))
        lines.append(f"{reps}{dur} · {b['label']} (zone {b['zone']}, {lo}–{hi} bpm)")
    return lines


def total_minutes(blocks: list[dict]) -> int:
    return round(sum(float(b["minutes"]) * (b.get("reps") or 1) for b in blocks or []))
