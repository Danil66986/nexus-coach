"""Calculs sportifs : zones cardiaques et charge d'entraînement (forme, fatigue, fraîcheur).

Mêmes formules que l'application, pour que le coach et l'app disent toujours la même chose.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from . import config

DEFAULT_IF = 0.65  # intensité supposée (endurance) quand une sortie n'a pas de fréquence cardiaque

ZONES = [
    (1, "Récupération", 0.5, 0.6),
    (2, "Endurance", 0.6, 0.7),
    (3, "Tempo", 0.7, 0.8),
    (4, "Seuil", 0.8, 0.9),
    (5, "VO2max", 0.9, 1.0),
]


def zone_bounds(max_hr: float, rest_hr: float, zone: int) -> tuple[int, int]:
    """Zones en % de la réserve cardiaque (Karvonen) : repos + % x (max - repos)."""
    _, _, lo, hi = ZONES[zone - 1]
    rest = rest_hr if 0 < rest_hr < max_hr else 0
    return round(rest + (max_hr - rest) * lo), round(rest + (max_hr - rest) * hi)


def zones_table(max_hr: float, rest_hr: float) -> list[dict]:
    out = []
    for z, name, _, _ in ZONES:
        lo, hi = zone_bounds(max_hr, rest_hr, z)
        out.append({"zone": z, "name": name, "bpm_min": lo, "bpm_max": hi})
    return out


def _trimp(minutes: float, x: float) -> float:
    return minutes * x * 0.64 * math.exp(1.92 * x)  # Banister


_REF = _trimp(60, 0.88)  # 1 h à ~88 % de la réserve cardiaque (seuil) = 100 points


def ride_load(duration_min: float, avg_hr: float | None, max_hr: float, rest_hr: float) -> tuple[float, bool]:
    """Charge d'une sortie (échelle TSS). Renvoie (points, estimée)."""
    if avg_hr and max_hr > rest_hr:
        x = min(max((avg_hr - rest_hr) / (max_hr - rest_hr), 0.0), 1.1)
        return 100 * _trimp(duration_min, x) / _REF, False
    return (duration_min / 60) * DEFAULT_IF * DEFAULT_IF * 100, True


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def compute_load(rides: list[dict], max_hr: float, rest_hr: float, today: date | None = None, total_days: int = 180) -> dict:
    """CTL (forme, 42 j), ATL (fatigue, 7 j), TSB = CTL - ATL (fraîcheur), jour par jour jusqu'à aujourd'hui."""
    today = today or config.today()
    start = today - timedelta(days=total_days - 1)
    daily: dict[date, float] = {}
    estimated = 0
    for r in rides:
        pts, est = ride_load(r.get("duration_min") or 0, r.get("avg_hr"), max_hr, rest_hr)
        estimated += 1 if est else 0
        d = parse_dt(r["started_at"]).astimezone(config.TZ).date()
        daily[d] = daily.get(d, 0.0) + pts

    k_ctl = 1 - math.exp(-1 / 42)
    k_atl = 1 - math.exp(-1 / 7)
    ctl = atl = 0.0
    days = []
    for i in range(total_days):
        d = start + timedelta(days=i)
        tss = daily.get(d, 0.0)
        tsb = ctl - atl  # fraîcheur du matin, avant la séance du jour
        ctl += (tss - ctl) * k_ctl
        atl += (tss - atl) * k_atl
        days.append({"date": d, "tss": tss, "ctl": ctl, "atl": atl, "tsb": tsb})
    return {"days": days, "estimated_rides": estimated, "ctl": ctl, "atl": atl, "tsb": days[-1]["tsb"]}


def form_label(tsb: float) -> tuple[str, str]:
    """(niveau, message) pour la fraîcheur."""
    if tsb > 25:
        return "tres_frais", "très frais (attention à ne pas perdre ta forme en te reposant trop)"
    if tsb > 5:
        return "frais", "frais : prêt pour une grosse séance ou une course"
    if tsb > -10:
        return "neutre", "neutre : bon équilibre entre charge et récupération"
    if tsb > -30:
        return "charge", "en charge productive : tu progresses, mais surveille la récupération"
    return "surcharge", "en surcharge : tu accumules de la fatigue, il faut de la récupération"


def week_stats(rides: list[dict], start: date, end: date) -> dict:
    """Totaux des sorties entre deux dates (incluses)."""
    sel = [r for r in rides if start <= parse_dt(r["started_at"]).astimezone(config.TZ).date() <= end]
    return {
        "rides": len(sel),
        "minutes": round(sum(r.get("duration_min") or 0 for r in sel)),
        "km": round(sum(float(r.get("distance_km") or 0) for r in sel), 1),
        "elevation_m": round(sum(r.get("elevation_m") or 0 for r in sel)),
    }
