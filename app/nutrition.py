"""Préparation d'une sortie : nutrition, hydratation, allure, matériel, récupération.

Repères généraux de nutrition du sport (consensus type ACSM / IOC), pas des conseils médicaux. Tout est calculé :
durée + intensité + météo + poids (si connu). Rien n'est inventé : sans poids, on donne les rapports par kilo.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from . import fitness
from .textutil import has, norm

NUM_WORDS = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8}
RIDE_WORDS = ("roul", "sortie", "sortir", "velo", "ride", "partir", "pedal", "balade", "cyclo", "course", "ravitail", "nutrition",
              "manger", "boire", "hydrat", "gel", "barre", "gourde", "bidon", "glucide", "repas", "alimentation")


def parse_duration(msg: str) -> int | None:
    """Durée en minutes : « 2h », « 2h30 », « 1 h 15 », « 90 min », « deux heures et demie », « une demi-heure »."""
    m = norm(msg)
    if re.search(r"demi[- ]?heure", m):
        return 30
    r = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|heures?)\s*(\d{1,2})?(?!\d)", m)
    if r:
        mins = round(float(r.group(1).replace(",", ".")) * 60) + (int(r.group(2)) if r.group(2) else 0)
        return mins if 15 <= mins <= 900 else None
    r = re.search(r"\b(un|une|deux|trois|quatre|cinq|six|sept|huit)\s+heures?(?:\s+et\s+(demie?|quart))?", m)
    if r:
        mins = NUM_WORDS[r.group(1)] * 60 + (30 if r.group(2) and r.group(2).startswith("demi") else 15 if r.group(2) else 0)
        return mins
    r = re.search(r"(\d{2,3})\s*(?:min|minutes?|mn)\b", m)
    if r:
        mins = int(r.group(1))
        return mins if 15 <= mins <= 900 else None
    return None


@dataclass
class RideRequest:
    minutes: int
    intensity: str          # easy | tempo | hard | race
    temp_c: float | None
    wet: bool
    intensity_given: bool


def parse_ride(msg: str, planned_kind: str | None = None) -> RideRequest | None:
    minutes = parse_duration(msg)
    m = norm(msg)
    if minutes is None or not has(m, *RIDE_WORDS):
        return None
    intensity, given = "easy", True
    if has(m, "course", "competition", "cyclosportive", "gran fondo", "marathon", "contre la montre"):
        intensity = "race"
    elif has(m, "intervalle", "fractionn", "seuil", "vo2", "30/30", "pyramide", "interval", "sprint", "dur", "intense", "a bloc"):
        intensity = "hard"
    elif has(m, "tempo", "sweet", "soutenu", "rythme"):
        intensity = "tempo"
    elif has(m, "recup", "tranquille", "cool", "balade", "facile", "endurance", "zone 2", "longue", "doucement"):
        intensity = "easy"
    else:
        given = False
        if planned_kind in ("tempo",):
            intensity = "tempo"
        elif planned_kind in ("threshold", "vo2", "hills", "sharpen"):
            intensity = "hard"
    temp = None
    t = re.search(r"(-?\d{1,2})\s*(?:°|degres?)", m)
    if t:
        temp = float(t.group(1))
    elif has(m, "canicule", "tres chaud", "etouffant"):
        temp = 33
    elif has(m, "chaud", "beau soleil", "grosse chaleur"):
        temp = 27
    elif has(m, "gel", "verglas", "negatif"):
        temp = 0
    elif has(m, "froid", "glacial"):
        temp = 4
    elif has(m, "frais", "fraiche"):
        temp = 12
    wet = has(m, "pluie", "pluvieux", "mouille", "averse", "humide")
    return RideRequest(minutes, intensity, temp, wet, given)


# ---------- chiffres ----------
def carb_rate(minutes: int, intensity: str) -> tuple[int, int, int]:
    """(bas, haut, cible) en g de glucides par heure."""
    if intensity == "easy":
        table = [(75, (0, 30, 20)), (120, (30, 45, 40)), (180, (40, 60, 50)), (270, (50, 70, 60)), (10**6, (60, 90, 70))]
    elif intensity == "tempo":
        table = [(60, (0, 30, 15)), (120, (40, 60, 50)), (180, (50, 70, 60)), (10**6, (60, 90, 70))]
    else:  # hard, race
        table = [(45, (0, 30, 15)), (90, (30, 60, 45)), (150, (50, 70, 60)), (240, (60, 90, 70)), (10**6, (70, 90, 80))]
    for limit, val in table:
        if minutes < limit:
            return val
    return table[-1][1]


def fluid_rate(temp: float | None, intensity: str) -> tuple[int, int]:
    """(bas, haut) en ml par heure."""
    t = 18 if temp is None else temp
    if t < 5:
        lo, hi = 350, 500
    elif t < 15:
        lo, hi = 450, 600
    elif t < 22:
        lo, hi = 500, 700
    elif t < 28:
        lo, hi = 600, 850
    else:
        lo, hi = 750, 1000
    if intensity in ("hard", "race"):
        lo, hi = lo + 50, hi + 50
    return lo, hi


def sodium_rate(temp: float | None, minutes: int) -> tuple[int, int] | None:
    t = 18 if temp is None else temp
    if t >= 28 or (t >= 24 and minutes >= 90):
        return 500, 800
    if minutes >= 120 or t >= 22:
        return 300, 500
    return None


def hours_text(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h} h{m:02d}" if h and m else (f"{h} h" if h else f"{m} min")


def _kg(ctx: dict) -> float | None:
    w = ((ctx.get("coach_profile") or {}).get("identity") or {}).get("weight_kg")
    if w:
        return float(w)
    for r in ctx.get("measurements") or []:
        if r.get("kind") == "weight_kg":
            return float(r["value"])
    return None


def ride_brief(ctx: dict, req: RideRequest, planned: dict | None) -> str:
    mins, kind = req.minutes, req.intensity
    hrs = mins / 60
    max_hr, rest_hr = ctx["max_hr"], ctx["rest_hr"]
    z = lambda n: fitness.zone_bounds(max_hr, rest_hr, n)
    L: list[str] = []

    label = {"easy": "sortie d'endurance", "tempo": "sortie tempo", "hard": "sortie d'intensité", "race": "course / effort maximal"}[kind]
    temp_txt = ""
    if req.temp_c is not None:
        temp_txt = f", autour de {req.temp_c:g}°C"
    L.append(f"## Ta {label} de {hours_text(mins)}{temp_txt}{' sous la pluie' if req.wet else ''}")

    # --- garde-fous ---
    flags = []
    if ctx["restrict_intense"] and kind in ("hard", "race", "tempo"):
        flags.append("⚠️ Tu as signalé une limitation : je te conseille de rester en endurance facile (zone 1-2) et d'éviter toute intensité tant que tu n'as pas eu l'avis d'un professionnel de santé.")
    level, _ = fitness.form_label(ctx["load"]["tsb"])
    if level == "surcharge" and kind in ("hard", "race"):
        flags.append("⚠️ Ta fraîcheur est très basse : une sortie intense maintenant augmente le risque de blessure ou de contre-performance. Fais plutôt de l'endurance facile.")
    if planned and planned.get("kind") not in (None, "event"):
        from . import context as cx  # import local : évite une dépendance circulaire
        pmin = cx.total_minutes(planned["blocks"])
        if pmin and mins > pmin * 1.5:
            flags.append(f"ℹ️ Ton plan prévoit « {planned['title']} » ({pmin} min). Rouler {hours_text(mins)} fait presque {round(mins / pmin * 100 - 100)} % de plus : ça peut passer si tu restes très facile, mais garde le reste de ta semaine tel quel (pas de rattrapage ensuite).")
    L += flags

    # --- allure ---
    L.append("\n## 🎯 Allure (zones cardiaques)")
    if kind == "easy":
        L.append(f"• Reste en **zone 2 : {z(2)[0]}–{z(2)[1]} bpm** (zone 1 en début de sortie : {z(1)[0]}–{z(1)[1]} bpm).")
        L.append(f"• Les 20 premières minutes, reste plutôt dans le bas de la zone 2 (vers {z(2)[0]}–{round((z(2)[0] + z(2)[1]) / 2)} bpm).")
        if mins >= 120:
            L.append("• Sur une sortie longue, ta fréquence cardiaque dérive vers le haut avec la fatigue et la chaleur : c'est normal. Ralentis un peu pour rester en zone 2 plutôt que de t'accrocher à la vitesse.")
    elif kind == "tempo":
        L.append(f"• Échauffement 15 min en zone 2 ({z(2)[0]}–{z(2)[1]} bpm), puis blocs en **zone 3 : {z(3)[0]}–{z(3)[1]} bpm**, avec des récupérations en zone 1.")
    elif kind == "hard":
        L.append(f"• Échauffement 15–20 min, puis intervalles en **zone 4 ({z(4)[0]}–{z(4)[1]} bpm)** ou **zone 5 ({z(5)[0]}–{z(5)[1]} bpm)**. Ta fréquence cardiaque met 2 à 3 minutes à monter : vise la zone en fin d'effort.")
        L.append(f"• Récupère en zone 1 ({z(1)[0]}–{z(1)[1]} bpm) entre les efforts. Retour au calme de 10 min.")
    else:
        L.append(f"• Pars **prudemment** : zone 3 ({z(3)[0]}–{z(3)[1]} bpm) les 20 premières minutes, puis monte vers la zone 4 ({z(4)[0]}–{z(4)[1]} bpm) si tout va bien. Garde du jus pour la fin.")

    # --- nutrition ---
    lo, hi, target = carb_rate(mins, kind)
    f_lo, f_hi = fluid_rate(req.temp_c, kind)
    na = sodium_rate(req.temp_c, mins)
    kg = _kg(ctx)

    L.append("\n## 🍽️ Avant la sortie")
    if mins < 60 and kind == "easy":
        L.append("• Rien de spécial : un repas normal 2 à 3 h avant, ou une petite collation (une banane, du pain avec de la confiture) 30 à 60 min avant.")
    else:
        pre = f" (soit environ {round(kg * 1)}–{round(kg * 2)} g pour {kg:g} kg)" if kg else " (1 à 2 g de glucides par kilo)"
        L.append(f"• Repas **2 à 3 h avant** : riche en glucides, peu gras et peu de fibres{pre}. Exemples : pâtes ou riz avec un peu de protéines, ou porridge avec une banane, ou pain avec confiture et un œuf.")
        L.append("• 30 à 60 min avant : une petite collation facile (banane, compote, pain d'épices) si tu as faim.")
    L.append(f"• Bois environ 400 à 500 ml d'eau dans les 2 h qui précèdent, puis par petites gorgées. Un café est possible si tu en bois d'habitude.")
    if mins >= 120 or kind in ("hard", "race"):
        L.append("• Ne teste jamais un produit nouveau le jour d'une grosse sortie ou d'une course : essaie-le avant, à l'entraînement.")

    L.append("\n## 🥤 Pendant la sortie")
    total_fluid = round(f_lo * hrs / 50) * 50, round(f_hi * hrs / 50) * 50
    bidons = max(1, math.ceil(((total_fluid[0] + total_fluid[1]) / 2) / 750))
    refill = f" Si la sortie passe près d'un point d'eau, refais le plein en route." if total_fluid[1] > bidons * 750 else ""
    L.append(f"• **Boisson : {f_lo}–{f_hi} ml par heure**, soit environ {total_fluid[0]}–{total_fluid[1]} ml sur la sortie. Prévois **{bidons} bidon{'s' if bidons > 1 else ''}** de 750 ml.{refill}")
    if target == 0 or (mins < 60 and kind == "easy"):
        L.append("• Glucides : pas nécessaires sur une sortie facile de moins d'une heure. De l'eau suffit.")
    else:
        total_c = round(target * hrs)
        pieces = max(1, round(total_c * 0.5 / 25))
        L.append(f"• **Glucides : {lo}–{hi} g par heure (cible : {target} g/h)**, soit environ **{total_c} g** sur la sortie.")
        L.append(f"  – Une moitié dans ta boisson (boisson énergétique ou sirop : lis l'étiquette, comptes ~30 g par bidon de 500 ml à 6 %).")
        L.append(f"  – L'autre moitié en solide : environ {pieces} prise{'s' if pieces > 1 else ''} de 25 g à choisir parmi : 1 gel, 1 barre de céréales, 1 banane, quelques pâtes de fruits.")
        L.append(f"• Mange **avant d'avoir faim** : première prise vers 20–30 min, puis toutes les 20–30 min. Bois quelques gorgées toutes les 10–15 min.")
        if target >= 70:
            L.append("• Au-delà de 60 g/h, mélange des sources (glucose + fructose, ex. gels et boisson différents) et entraîne ton ventre à l'avance pour bien le tolérer.")
    if na:
        L.append(f"• **Sodium : {na[0]}–{na[1]} mg par heure** (comprimés d'électrolytes ou boisson salée), surtout si tu transpires beaucoup ou s'il fait chaud.")
    if req.temp_c is not None and req.temp_c >= 28:
        L.append("• Forte chaleur : pars très tôt ou tard, arrose-toi la nuque et les bras, réduis l'allure de 5 à 10 bpm, et arrête-toi si tu as des vertiges, des frissons ou des maux de tête.")
    if req.temp_c is not None and req.temp_c <= 8:
        L.append("• Il fait froid : bois quand même (on a moins soif par temps froid), garde une boisson tiède si possible, et couvre les extrémités (gants, couvre-chaussures).")

    L.append("\n## 🎒 À emporter")
    kit = [f"{bidons} bidon{'s' if bidons > 1 else ''} plein{'s' if bidons > 1 else ''}"]
    if target > 0 and mins >= 60:
        kit.append("tes gels / barres (prévois-en 1 de plus que prévu)")
    kit += ["chambre à air de rechange, démonte-pneus et pompe", "téléphone chargé, un peu d'argent ou une carte"]
    if req.wet or (req.temp_c is not None and req.temp_c < 12):
        kit.append("coupe-vent ou veste de pluie, gants")
    if req.temp_c is not None and req.temp_c >= 25:
        kit.append("crème solaire, lunettes")
    if mins >= 150:
        kit.append("un sandwich ou une barre salée pour un vrai ravitaillement")
    L.append("• " + " · ".join(kit))

    L.append("\n## 🔄 Après la sortie")
    if kg:
        carb_after = f"{round(kg * 1.0)}–{round(kg * 1.2)} g de glucides et {round(kg * 0.25)}–{round(kg * 0.3)} g de protéines"
    else:
        carb_after = "1 à 1,2 g de glucides et 0,25 à 0,3 g de protéines par kilo"
    if mins >= 120 or kind in ("hard", "race"):
        L.append(f"• Dans les 1 à 2 h : {carb_after}. Exemple : riz ou pâtes avec du poulet ou du poisson, ou un yaourt grec avec des fruits et des céréales.")
    else:
        L.append("• Un repas normal et équilibré suffit dans l'heure ou les deux heures qui suivent.")
    L.append("• Réhydrate-toi : si tu t'es pesé avant et après, bois 1,2 à 1,5 L par kilo perdu. Sinon, bois jusqu'à ce que ton urine soit claire.")
    L.append("• Dors suffisamment cette nuit : c'est là que tu progresses.")

    L.append("\nCes repères généraux de nutrition du sport ne remplacent pas un avis médical ou diététique. En cas de diabète, de maladie ou de traitement, parles-en d'abord à un professionnel de santé.")
    return "\n".join(L)


def nutrition_help() -> str:
    return (
        "Dis-moi ce que tu prévois et je te prépare tout : par exemple **« je vais rouler 2 h »**, **« sortie longue de 3 h 30, il fera 28° »** "
        "ou **« séance de seuil de 90 min »**.\nJe te donne : repas d'avant, glucides et boisson à l'heure, sodium, allure en bpm, matériel et récupération.\n\n"
        "Repères rapides :\n• Moins d'1 h facile : de l'eau suffit.\n• 1 h 30 à 2 h 30 : 40 à 60 g de glucides par heure, 500 à 800 ml de boisson par heure.\n"
        "• Plus de 3 h : jusqu'à 60–90 g par heure, à t'entraîner à l'avance.\n• Après un gros effort : glucides + protéines dans les 1 à 2 h."
    )
