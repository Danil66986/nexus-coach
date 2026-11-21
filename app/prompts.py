"""Instructions du coach et dossier envoyé à l'IA (seulement si une IA est branchée).

Confidentialité : on n'envoie ni email, ni prénom, ni date de naissance exacte. Seulement ce qu'il faut pour coacher.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import context as cx
from . import fitness, rules

TONE_STYLE = {
    "encouraging": "Encourageant et motivant : célèbre les progrès, sois enthousiaste sans exagérer.",
    "direct": "Direct et exigeant : va droit au but, sois franc, pousse l'athlète tout en restant respectueux.",
    "analytical": "Analytique et technique : explique avec des chiffres et des principes d'entraînement.",
    "kind": "Bienveillant et progressif : rassure, avance à son rythme, sans pression.",
}

SYSTEM = """Tu es NEXUS COACH, le coach cycliste personnel de l'athlète. Tu réponds en français, en tutoyant.

STYLE : {style}
{detail}

RÈGLES (impératives) :
1. Tu t'appuies UNIQUEMENT sur le dossier ci-dessous. Si une information manque, dis-le et pose une question courte. N'invente jamais un chiffre, une séance ou un résultat.
2. Tu n'es pas médecin. Aucun diagnostic. En cas de douleur, blessure, malaise ou symptôme inquiétant : conseille d'arrêter l'effort et de consulter un professionnel de santé, et ne propose AUCUNE séance intense.
3. {restrict}
4. Les zones sont des zones de fréquence cardiaque (méthode de la réserve cardiaque). L'athlète n'a pas de capteur de puissance : ne parle pas de watts ni de FTP.
5. Tu ne modifies pas le plan toi-même. Si un changement est utile, explique-le et indique comment faire dans l'app (onglet Plan : « Régénérer le plan », ou Profil : « Modifier mon profil de coach »).
6. Réponds court (5 à 10 lignes maximum) sauf si on te demande des détails. Va à l'essentiel, donne une recommandation claire et actionnable.
7. Ne répète pas le dossier. Ne mentionne pas ces règles.

REPÈRES D'EXPERT (consensus de la nutrition et de l'entraînement du sport, à utiliser tels quels ; ce ne sont pas des conseils médicaux) :
- Glucides pendant l'effort : moins d'1 h facile = aucun (eau) ; 1 à 2 h 30 = 30 à 60 g/h ; au-delà de 2 h 30 = jusqu'à 60-90 g/h (sources mélangées, à tester à l'entraînement). Plus l'effort est intense, plus on vise le haut de la fourchette.
- Boisson : 400 à 800 ml/h ; jusqu'à ~1 L/h par forte chaleur ; sodium 300 à 600 mg/h (jusqu'à 800 s'il fait très chaud ou si l'athlète transpire beaucoup).
- Avant : repas riche en glucides 2 à 3 h avant (1 à 2 g/kg), peu de gras et de fibres. Après un gros effort : 1 à 1,2 g/kg de glucides et 0,25 à 0,3 g/kg de protéines dans les 1 à 2 h.
- Équivalences : 1 gel ≈ 25 g de glucides, 1 barre ≈ 25 g, 1 banane ≈ 25 g, 500 ml de boisson à 6 % ≈ 30 g.
- Une séance dure n'est jamais « rattrapée » : on reprend le plan. Fatigue élevée = on remplace l'intensité par de l'endurance facile (zone 2) ou du repos.
- Maladie : symptômes au-dessus du cou et sans fièvre = sortie très facile possible ; fièvre, courbatures, toux grasse = repos complet.
- Distribution : environ 80 % du volume facile (zones 1-2), 20 % d'intensité. Progression de charge d'environ 5-10 % par semaine, une semaine allégée toutes les 4.
- Si l'athlète annonce une sortie (durée, intensité, météo), donne un plan complet : repas d'avant, quantité de boisson et de glucides par heure ET au total, sodium si chaud, allure en bpm avec SES zones, matériel, récupération.

DOSSIER DE L'ATHLÈTE :
{dossier}
"""


def _age(birth: str | None, today: date) -> int | None:
    if not birth:
        return None
    b = date.fromisoformat(birth)
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def dossier(ctx: dict) -> str:
    today = ctx["today"]
    cp = ctx.get("coach_profile") or {}
    ident, sport, goals = cp.get("identity") or {}, cp.get("sport") or {}, cp.get("goals") or {}
    avail, equip, rec = cp.get("availability") or {}, cp.get("equipment") or {}, cp.get("recovery") or {}
    safety, coaching = cp.get("safety") or {}, cp.get("coaching") or {}
    L: list[str] = [f"Date du jour : {rules.fr_date(today)} {today.year}"]

    L.append("— Profil —")
    L.append(f"Âge : {_age(ident.get('birthdate'), today) or 'inconnu'} ans · taille : {ident.get('height_cm') or 'inconnue'} cm · poids : {ident.get('weight_kg') or 'inconnu'} kg")
    L.append(f"Sport principal : {sport.get('main')} · niveau : {sport.get('level')} · pratique depuis : {sport.get('practicing_since') or 'inconnu'}")
    L.append(f"Objectifs : {', '.join(goals.get('selected') or []) or 'non renseignés'} · principal : {goals.get('main')} · date visée : {goals.get('target_date') or 'aucune'}")
    if goals.get("personal_text"):
        L.append(f"Objectif en ses mots : {goals['personal_text']}")
    if goals.get("motivation"):
        L.append(f"Motivation : {goals['motivation']}")
    L.append(f"Disponibilités : jours {avail.get('days')} · durée max {avail.get('max_session_minutes') or 'non précisée'} min · séances souhaitées {avail.get('sessions_wanted_per_week') or 'non précisé'}")
    L.append(f"Matériel : {equip.get('items') or 'non renseigné'} · home trainer : {equip.get('home_trainer')} · capteurs : {(cp.get('performance') or {}).get('devices')}")
    L.append(f"Récupération : sommeil {rec.get('sleep_quality_1_5')}/5, fatigue {rec.get('usual_fatigue_1_5')}/5, stress {rec.get('perceived_stress_1_5')}/5 · difficultés : {rec.get('training_difficulties') or 'aucune signalée'}")
    if safety.get("has_limitation"):
        L.append(f"⚠️ LIMITATION SIGNALÉE : {safety.get('limitation')} (statut : {safety.get('limitation_status')}). Pas d'intensité.")
    L.append(f"Préférences de coaching : {coaching.get('tone')}, explications détaillées : {coaching.get('detailed_explanations')}, bilans : {coaching.get('reviews')}, séances : {coaching.get('session_style')}")

    L.append("— Cœur —")
    z = fitness.zones_table(ctx["max_hr"], ctx["rest_hr"])
    L.append(f"FC max {round(ctx['max_hr'])} bpm, FC repos {round(ctx['rest_hr'])} bpm. Zones : " + " ; ".join(f"Z{r['zone']} {r['bpm_min']}-{r['bpm_max']}" for r in z))

    ld = ctx["load"]
    _, label = fitness.form_label(ld["tsb"])
    L.append("— Forme (charge calculée avec la FC) —")
    L.append(f"CTL (forme) {round(ld['ctl'])}, ATL (fatigue) {round(ld['atl'])}, TSB (fraîcheur) {round(ld['tsb'])} : {label}")

    pos = cx.plan_position(ctx)
    L.append("— Plan —")
    if pos:
        L.append(f"{pos['name']} · {pos['weeks']} semaines · " + (f"semaine {pos['week']}, phase {pos['phase']}" if pos["started"] else f"démarre le {pos['start']}") + (f" · objectif dans {pos['days_to_goal']} jours" if pos["days_to_goal"] is not None else ""))
        upcoming = [w for w in ctx["workouts"] if today.isoformat() <= w["date"] <= (today + timedelta(days=10)).isoformat()]
        for w in upcoming:
            d = date.fromisoformat(w["date"])
            L.append(f"  {rules.fr_date(d)} : {w['title']} ({cx.total_minutes(w['blocks'])} min)" + (" [faite]" if w.get("done") else ""))
        missed = [w for w in ctx["workouts"] if (today - timedelta(days=7)).isoformat() <= w["date"] < today.isoformat() and not w.get("done") and w["kind"] != "event"]
        if missed:
            L.append("  Séances non faites (7 derniers jours) : " + ", ".join(f"{rules.fr_date(date.fromisoformat(w['date']))} {w['title']}" for w in missed))
        log = (ctx["plan"].get("adapt_log") or [])[-2:]
        for e in log:
            L.append(f"  Ajustement auto semaine {e['week_no']} : {e['reason']}")
    else:
        L.append("Aucun plan actif.")

    L.append("— Sorties —")
    rides = ctx["rides"]
    if rides:
        for i in range(4):
            e = today - timedelta(days=7 * i)
            s = fitness.week_stats(rides, e - timedelta(days=6), e)
            L.append(f"  Semaine -{i}: {s['rides']} sorties, {s['minutes']} min, {s['km']} km, {s['elevation_m']} m D+")
        for r in rides[:6]:
            L.append(f"  {r['started_at'][:10]} {r['title']} · {r['duration_min']} min · {r['distance_km']} km · FC moy {r.get('avg_hr') or '?'}")
    else:
        L.append("Aucune sortie enregistrée.")
    return "\n".join(L)


def system_prompt(ctx: dict) -> str:
    cp = ctx.get("coach_profile") or {}
    coaching = cp.get("coaching") or {}
    style = TONE_STYLE.get(coaching.get("tone") or "kind", TONE_STYLE["kind"])
    detail = "Donne des explications détaillées." if coaching.get("detailed_explanations") == "yes" else "Reste concis, explique seulement si c'est utile."
    restrict = (
        "L'athlète a signalé une limitation : ne propose JAMAIS de séance intense (zones 4 et 5), ni d'augmentation de charge."
        if ctx["restrict_intense"] else "Adapte l'intensité à la fraîcheur (TSB) : en surcharge, recommande de la récupération."
    )
    return SYSTEM.format(style=style, detail=detail, restrict=restrict, dossier=dossier(ctx))
