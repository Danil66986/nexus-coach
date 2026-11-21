"""Réponses expertes du coach, sans IA externe : elles s'appuient uniquement sur tes données.

C'est le socle du coach. Si une IA est branchée, ces règles servent encore pour la sécurité (douleur, malaise) et de secours.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

from . import context as cx
from . import fitness, knowledge, nutrition
from .textutil import has, norm  # noqa: F401  (norm est réexporté pour les autres modules)

DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
PHASE_FR = {"base": "Base", "build": "Développement", "taper": "Affûtage", "recovery": "Récupération"}
PHASE_ADVICE = {
    "base": "On construit les fondations : beaucoup d'endurance en zone 2, de la régularité, très peu d'intensité.",
    "build": "On monte en puissance : les séances d'intensité sont le cœur de la semaine, le reste doit rester facile pour les encaisser.",
    "taper": "On allège pour arriver frais : moins de volume, un peu de tonus, et du repos. Ne cherche pas à rattraper quoi que ce soit.",
    "recovery": "Semaine de récupération : c'est là que ton corps progresse vraiment. Ne la transforme pas en semaine de charge.",
}


def fr_date(d: date) -> str:
    return f"{DAYS_FR[d.weekday()]} {d.day} {MONTHS_FR[d.month - 1]}"


def tone(ctx: dict) -> str:
    return ((ctx.get("coach_profile") or {}).get("coaching") or {}).get("tone") or "kind"


def closer(ctx: dict, kind: str = "ok") -> str:
    t = tone(ctx)
    lines = {
        "encouraging": {"ok": "Tu fais du super boulot, continue comme ça ! 🔥", "rest": "Le repos aussi, ça se mérite. Tu reviens plus fort ! 💪"},
        "direct": {"ok": "Applique le plan, sans négocier.", "rest": "Pas de séance cachée : repos, c'est repos."},
        "analytical": {"ok": "Les données sont cohérentes avec le plan : on poursuit.", "rest": "Charge nulle aujourd'hui : c'est le signal d'une récupération qui fait son travail."},
        "kind": {"ok": "Avance à ton rythme, l'important c'est la régularité. 🌱", "rest": "Prends soin de toi, le plan sait t'attendre. 🌱"},
    }
    return lines.get(t, lines["kind"])[kind]


# ---------- briques ----------
def session_text(ctx: dict, w: dict) -> str:
    mins = cx.total_minutes(w["blocks"])
    head = f"{w['title']}" + (f" · {mins} min" if mins else "")
    lines = [head]
    lines += [f"  • {l}" for l in cx.describe_blocks(w["blocks"], ctx["max_hr"], ctx["rest_hr"])]
    if w.get("notes"):
        lines.append(f"💡 {w['notes']}")
    return "\n".join(lines)


def load_text(ctx: dict) -> str:
    L = ctx["load"]
    level, label = fitness.form_label(L["tsb"])
    txt = (
        f"Forme (CTL) : {round(L['ctl'])} · Fatigue (ATL) : {round(L['atl'])} · Fraîcheur (TSB) : {round(L['tsb'])}.\n"
        f"Tu es {label}."
    )
    advice = {
        "surcharge": "Priorité à la récupération : repos ou 30 à 45 min très faciles en zone 1, aucune intensité pendant 2 à 3 jours.",
        "charge": "Garde les séances d'intensité du plan, mais ne rajoute rien. Dors suffisamment et surveille ta fréquence cardiaque au repos.",
        "neutre": "Tu peux suivre le plan tel quel.",
        "frais": "Bon moment pour une séance de qualité ou une sortie plus ambitieuse.",
        "tres_frais": "Tu es peut-être trop au repos : remets de la charge progressivement, sans à-coup.",
    }[level]
    txt += f"\n👉 {advice}"
    if L["estimated_rides"]:
        txt += f"\n(Note : {L['estimated_rides']} sorties sans fréquence cardiaque ont une charge estimée.)"
    if ctx["restrict_intense"]:
        txt += "\n⚠️ Tu as signalé une limitation : je ne te proposerai pas d'intensité."
    return txt


def week_text(ctx: dict) -> str:
    today = ctx["today"]
    end = today + timedelta(days=6)
    ws = [w for w in ctx["workouts"] if today.isoformat() <= w["date"] <= end.isoformat()]
    if not ws:
        return "Je ne vois aucune séance prévue dans les 7 prochains jours. Dans l'onglet Plan, génère ou régénère ton plan."
    lines = ["Tes 7 prochains jours :"]
    for w in ws:
        d = date.fromisoformat(w["date"])
        mins = cx.total_minutes(w["blocks"])
        mark = "✅ " if w.get("done") else ""
        lines.append(f"• {fr_date(d)} : {mark}{w['title']}" + (f" ({mins} min)" if mins else ""))
    return "\n".join(lines)


def stats_text(ctx: dict) -> str:
    today = ctx["today"]
    rides = ctx["rides"]
    w0 = fitness.week_stats(rides, today - timedelta(days=6), today)
    w1 = fitness.week_stats(rides, today - timedelta(days=13), today - timedelta(days=7))
    m4 = fitness.week_stats(rides, today - timedelta(days=27), today)
    if not rides:
        return "Je n'ai encore aucune sortie. Connecte Strava dans l'onglet Sorties pour que je puisse faire ton bilan."

    def h(m: int) -> str:
        return f"{m // 60} h{m % 60:02d}"

    diff = w0["minutes"] - w1["minutes"]
    trend = "stable" if abs(diff) < 15 else (f"en hausse de {h(diff)}" if diff > 0 else f"en baisse de {h(-diff)}")
    lines = [
        "Ton bilan :",
        f"• 7 derniers jours : {w0['rides']} sorties, {h(w0['minutes'])}, {w0['km']} km, {w0['elevation_m']} m D+ ({trend} vs la semaine d'avant).",
        f"• 4 dernières semaines : {m4['rides']} sorties, {h(m4['minutes'])} au total, soit environ {h(round(m4['minutes'] / 4))} par semaine.",
    ]
    longest = max(rides[:60], key=lambda r: r.get("duration_min") or 0, default=None)
    if longest:
        lines.append(f"• Plus longue sortie récente : {longest['duration_min']} min ({longest['title']}).")
    done = [w for w in ctx["workouts"] if w["date"] <= today.isoformat() and w["kind"] != "event"]
    if done:
        k = sum(1 for w in done[-14:] if w.get("done"))
        lines.append(f"• Séances du plan faites sur les 14 derniers jours prévus : {k}/{len(done[-14:])}.")
    return "\n".join(lines)


def zones_text(ctx: dict) -> str:
    rows = fitness.zones_table(ctx["max_hr"], ctx["rest_hr"])
    lines = [f"Tes zones cardiaques (FC max {round(ctx['max_hr'])}, repos {round(ctx['rest_hr'])}) :"]
    lines += [f"• Zone {r['zone']} · {r['name']} : {r['bpm_min']}–{r['bpm_max']} bpm" for r in rows]
    lines.append("Elles se calculent avec ta réserve cardiaque (FC repos + % × (FC max − FC repos)). Tu les règles dans Profil.")
    return "\n".join(lines)


def goal_text(ctx: dict) -> str:
    cp = ctx.get("coach_profile") or {}
    goals = cp.get("goals") or {}
    pos = cx.plan_position(ctx)
    if not goals and not pos:
        return "Je ne connais pas encore ton objectif : termine ton profil de coach dans Profil."
    lines = []
    if goals.get("personal_text"):
        lines.append(f"Ton objectif : « {goals['personal_text']} »")
    if pos:
        lines.append(f"Ton plan : {pos['name']}.")
        if pos["started"]:
            lines.append(f"Tu es en semaine {pos['week']} sur {pos['weeks']}" + (f" · phase {PHASE_FR.get(pos['phase'], pos['phase'])}." if pos["phase"] else "."))
            if pos["phase"] in PHASE_ADVICE:
                lines.append(PHASE_ADVICE[pos["phase"]])
        else:
            lines.append(f"Il démarre le {fr_date(pos['start'])}.")
        if pos["days_to_goal"] is not None:
            lines.append(f"🏁 Objectif dans {pos['days_to_goal']} jours." if pos["days_to_goal"] >= 0 else "La date de ton objectif est passée.")
    return "\n".join(lines)


def missed_text(ctx: dict) -> str:
    today = ctx["today"]
    missed = [w for w in ctx["workouts"] if today - timedelta(days=7) <= date.fromisoformat(w["date"]) < today and not w.get("done") and w["kind"] != "event"]
    if not missed:
        return "Je ne vois aucune séance manquée sur les 7 derniers jours. Bravo, tu es dans le plan."
    lines = [f"Séances non faites ces 7 derniers jours : {len(missed)}."]
    lines += [f"• {fr_date(date.fromisoformat(w['date']))} : {w['title']}" for w in missed]
    lines.append(
        "Mon conseil : ne rattrape pas. Empiler deux séances dures pour « compenser » augmente le risque de blessure sans te faire progresser plus vite. "
        "Reprends simplement le plan à la prochaine séance. Chaque semaine terminée, le plan s'ajuste tout seul si tu en as manqué plusieurs."
    )
    if len(missed) >= 3:
        lines.append("Si la vie est chargée en ce moment, dis-le-moi : on peut passer à moins de séances par semaine dans ton profil de coach.")
    return "\n".join(lines)


def pain_reply(msg: str, ctx: dict) -> str:
    if has(msg, "poitrine", "palpitation", "malaise", "vertige", "evanou", "essouffl", "souffle", "bras gauche"):
        return (
            "⚠️ Ce que tu décris peut être sérieux. Arrête l'effort et ne fais pas de sport. "
            "Si les symptômes sont forts ou persistent, appelle le 15 (SAMU) ou le 112 sans attendre. "
            "Parles-en à un médecin avant de reprendre. Je ne suis pas un professionnel de santé et je ne peux pas poser de diagnostic."
        )
    return (
        "Je suis désolé que tu aies mal. Je ne peux pas poser de diagnostic, et je ne dois pas te prescrire d'effort dans ce cas.\n"
        "• Une douleur qui apparaît à l'effort, qui s'aggrave, ou qui dure plus de 2 à 3 jours mérite l'avis d'un médecin du sport ou d'un kinésithérapeute.\n"
        "• En attendant, évite les séances d'intensité. Si tu roules, reste très facile (zone 1) et arrête-toi si la douleur augmente.\n"
        "• Quand tu auras un avis, mets à jour ton profil de coach (Récupération et ressenti) : le plan n'enverra alors plus de séances intenses.\n"
        + ("Tu as déjà signalé une limitation : le plan en tient compte." if ctx["restrict_intense"] else "")
    ).strip()


def today_reply(ctx: dict, offset: int = 0) -> str:
    d = ctx["today"] + timedelta(days=offset)
    label = "Aujourd'hui" if offset == 0 else "Demain"
    w = cx.workout_on(ctx, d)
    if not ctx["plan"] and not w:
        return "Tu n'as pas encore de plan d'entraînement. Dans l'onglet Plan, appuie sur « Générer mon plan d'entraînement »."
    if not w:
        return f"{label} ({fr_date(d)}), aucune séance n'est prévue : c'est un jour de repos.\n{closer(ctx, 'rest')}"
    done = " ✅ (déjà faite)" if w.get("done") else ""
    pos = cx.plan_position(ctx)
    ctxline = f"Semaine {w.get('week_no')} · {PHASE_FR.get(w.get('phase'), '')}\n" if w.get("week_no") else ""
    text = f"{label} ({fr_date(d)}){done} :\n{ctxline}{session_text(ctx, w)}"
    L = ctx["load"]
    level, _ = fitness.form_label(L["tsb"])
    if level == "surcharge" and w.get("kind") in ("tempo", "threshold", "vo2", "hills", "sharpen"):
        text += "\n⚠️ Ta fraîcheur est très basse : si tu te sens lourd, remplace cette séance par de l'endurance facile en zone 2."
    return text + f"\n{closer(ctx)}" if pos else text


HELP = (
    "Je suis ton coach. Je connais ton profil, ton plan, tes sorties et ta forme. Tu peux me demander par exemple :\n"
    "• **« Je vais rouler 2 h »** : je te prépare toute la sortie (nutrition, boisson, allure, matériel, récupération)\n"
    "• « Ma séance d'aujourd'hui » ou « Et demain ? »\n"
    "• « Pourquoi cette séance ? » ou « Comment réussir mon 30/30 ? »\n"
    "• « Comment est ma forme ? », « Mon bilan », « Mes zones »\n"
    "• « Je suis fatigué », « Je n'ai pas envie de rouler », « Je suis malade »\n"
    "• « Où j'en suis de mon objectif ? », « J'ai raté des séances »"
)


def _planned_today(ctx: dict) -> dict | None:
    return cx.workout_on(ctx, ctx["today"])


def _form_level(ctx: dict) -> str:
    return fitness.form_label(ctx["load"]["tsb"])[0]


def answer(message: str, ctx: dict) -> tuple[str, str]:
    """Renvoie (réponse, intention)."""
    m = norm(message)
    planned = _planned_today(ctx)
    if has(m, "douleur", "douloureux", "mal au", "mal a", "blessure", "blesse", "tendin", "genou", "claquage", "fracture", "poitrine",
           "palpitation", "malaise", "vertige", "evanou", "crampe", "entorse", "inflammation", "souffle"):
        return pain_reply(m, ctx), "pain"
    if has(m, "malade", "fievre", "grippe", "rhume", "toux", "angine", "gastro", "covid", "mal de gorge", "nez qui coule"):
        return knowledge.sick_reply(), "sick"
    # « je vais rouler 2h » : préparation complète de la sortie (avant « aujourd'hui » qui pourrait aussi apparaître dans la phrase)
    req = nutrition.parse_ride(message, (planned or {}).get("kind"))
    if req:
        return nutrition.ride_brief(ctx, req, planned), "ride"
    if has(m, "manger", "nutrition", "boire", "hydrat", "gel", "glucide", "alimentation", "repas", "ravitail", "bidon", "gourde"):
        return nutrition.nutrition_help(), "nutrition"
    if has(m, "pourquoi", "a quoi sert", "a quoi ca sert", "but de", "utilite"):
        kind = knowledge.kind_from_text(m) or (planned or {}).get("kind")
        return (knowledge.why_text(kind), "why") if kind in knowledge.PURPOSE else ("De quelle séance veux-tu parler ? (par exemple « pourquoi le seuil ? » ou « à quoi sert une sortie longue ? »)", "why")
    if has(m, "comment faire", "comment reussir", "comment aborder", "comment gerer", "comment realiser", "comment bien", "comment dois", "conseil pour ma seance"):
        kind = knowledge.kind_from_text(m) or (planned or {}).get("kind")
        return (knowledge.how_text(kind), "howto") if kind in knowledge.PURPOSE else ("De quelle séance veux-tu parler ? (par exemple « comment réussir mon 30/30 ? »)", "howto")
    if has(m, "je suis fatigu", "je suis creve", "suis creve", "epuise", "jambes lourdes", "jambe lourde", "suis cuit", "pas en forme", "pas la forme", "pas frais", "lourd"):
        return knowledge.tired_reply(_form_level(ctx), (planned or {}).get("kind"), (planned or {}).get("title")), "tired"
    if has(m, "motiv", "flemme", "pas envie", "envie de rien", "demotiv", "decourag", "lassitude"):
        return knowledge.motivation_reply(tone(ctx)), "motivation"
    if has(m, "sommeil", "dormir", "insomnie", "mal dormi", "dors"):
        return knowledge.sleep_reply(), "sleep"
    if has(m, "demain"):
        return today_reply(ctx, 1), "tomorrow"
    if has(m, "aujourd", "ce soir", "ce matin", "seance du jour", "je fais quoi", "que dois", "quoi faire", "au programme"):
        return today_reply(ctx, 0), "today"
    if has(m, "rate", "saute", "manque", "pas pu", "pas fait", "oublie", "rattrap"):
        return missed_text(ctx), "missed"
    if has(m, "semaine", "planning", "programme", "prochains jours"):
        return week_text(ctx), "week"
    if has(m, "zone", "zones"):
        return zones_text(ctx), "zones"
    if has(m, "forme", "fatigue", "fatigu", "fraicheur", "charge", "ctl", "atl", "tsb", "recup", "repos", "frais"):
        return load_text(ctx), "load"
    if has(m, "bilan", "stats", "statistique", "resume", "progres", "derniers", "kilometre", "km", "denivele", "combien"):
        return stats_text(ctx), "stats"
    if has(m, "objectif", "course", "echeance", "ou j en suis", "phase", "plan"):
        return goal_text(ctx), "goal"
    if has(m, "bonjour", "salut", "hello", "coucou", "aide", "help", "que peux", "tu sais faire"):
        return HELP, "help"
    return "Je n'ai pas bien compris. " + HELP, "fallback"


def brief(ctx: dict) -> str:
    """Le point du jour : séance, forme, avancement."""
    name = (ctx["profile"] or {}).get("name") or ""
    hi = f"Bonjour {name} !" if name else "Bonjour !"
    parts = [hi, today_reply(ctx, 0).replace(f"\n{closer(ctx)}", ""), load_text(ctx)]
    pos = cx.plan_position(ctx)
    if pos and pos["started"] and pos["phase"] in PHASE_ADVICE:
        parts.append(PHASE_ADVICE[pos["phase"]])
    parts.append(closer(ctx))
    return "\n\n".join(parts)
