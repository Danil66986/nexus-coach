"""Connaissances d'entraînement du coach : à quoi sert chaque séance, comment la réussir, et conseils du quotidien."""
from __future__ import annotations

from .textutil import has

PURPOSE: dict[str, dict[str, str]] = {
    "endurance": {
        "name": "l'endurance de base (zone 2)",
        "why": "Elle développe ton « moteur aérobie » : plus de capillaires, de mitochondries, une meilleure utilisation des graisses. C'est la base de tout, et elle se fait sans te fatiguer à l'excès, donc tu peux en faire beaucoup.",
        "how": "• Reste en zone 2, même si tu te sens en forme et même si ça te paraît lent.\n• Tu dois pouvoir parler en phrases complètes.\n• Garde une cadence fluide (85–95 tours par minute) et pédale en rond.",
        "mistake": "Rouler trop vite : en zone 3 « confortable », tu accumules de la fatigue sans le bénéfice de l'endurance ni celui de l'intensité.",
    },
    "long": {
        "name": "la sortie longue",
        "why": "Elle habitue ton corps à tenir longtemps : endurance musculaire, gestion de l'énergie, du ravitaillement et du mental. C'est la séance clé de la semaine pour la distance.",
        "how": "• Pars doucement et reste en zone 2 la majeure partie du temps.\n• Mange et bois dès les 20–30 premières minutes, sans attendre d'avoir faim ou soif.\n• Si la séance contient un finish ou un bloc tempo, ne le commence que si tu te sens bien.",
        "mistake": "Partir trop fort : une sortie longue se gagne sur la fin, pas au début. Et oublier de manger.",
    },
    "recovery": {
        "name": "la récupération active",
        "why": "Elle favorise la circulation et la récupération sans ajouter de fatigue. Ton corps progresse pendant le repos, pas pendant l'effort : cette séance protège tes séances dures.",
        "how": "• Très facile, zone 1, jambes libres, grande cadence et petit braquet.\n• Si tu as des jambes lourdes, raccourcis ou arrête.",
        "mistake": "La transformer en séance « un peu plus dure ». Une récupération trop rapide n'est plus une récupération.",
    },
    "tempo": {
        "name": "le tempo (zone 3)",
        "why": "Il améliore ta capacité à tenir un effort soutenu longtemps et ta résistance à la fatigue, avec un coût de récupération raisonnable. Très efficace pour les longues distances.",
        "how": "• Monte progressivement en zone 3 et stabilise-toi, sans à-coup.\n• Respiration marquée mais contrôlée, tu peux dire quelques mots.\n• Garde la même intensité du premier au dernier bloc.",
        "mistake": "Partir trop fort sur le premier bloc et s'effondrer sur le dernier. Le but est la régularité.",
    },
    "threshold": {
        "name": "le seuil (zone 4)",
        "why": "Il repousse le niveau d'effort que tu peux tenir longtemps (ton seuil). C'est la séance qui fait progresser le plus vite la vitesse « de croisière », mais aussi l'une des plus fatigantes.",
        "how": f"• Échauffe-toi bien (15 min + quelques accélérations).\n• Ta fréquence cardiaque met 2 à 3 minutes à monter : vise la zone 4 en fin d'intervalle, ne t'affole pas si elle est basse au début.\n• Reste régulier : le dernier intervalle doit ressembler au premier.\n• Récupère vraiment en zone 1 entre les intervalles.",
        "mistake": "Dépasser la zone 4 sur les premiers intervalles. Un effort trop dur au début ruine la séance.",
    },
    "vo2": {
        "name": "le VO2max (zone 5)",
        "why": "Il augmente ta puissance aérobie maximale, c'est-à-dire le « plafond » de ton moteur. Efforts courts et très intenses, à ne faire que frais et pas trop souvent.",
        "how": "• Échauffement complet avec 2 ou 3 accélérations.\n• Chaque effort est très dur mais tenable : le dernier doit être au même niveau que le premier.\n• Ta fréquence cardiaque monte lentement : elle sera en zone 5 surtout sur la fin de chaque effort.\n• Récupération complète entre les efforts, en zone 1.",
        "mistake": "Partir à fond sur le premier effort et ne pas pouvoir finir la série. Choisis une intensité que tu peux répéter.",
    },
    "hills": {
        "name": "les côtes / la force",
        "why": "Elles développent la force spécifique à la montée et l'économie de pédalage, avec une charge d'impact très faible.",
        "how": "• Reste assis, dos droit, cadence régulière.\n• Pour les séances de force : 50–60 tours par minute avec un gros braquet, sans balancer le bassin.\n• Descends tranquillement pour récupérer.",
        "mistake": "Se lever sur les pédales et forcer sur les genoux. Arrête-toi à la moindre gêne articulaire.",
    },
    "sharpen": {
        "name": "l'affûtage",
        "why": "À l'approche de ton objectif, on garde un peu de tonus sans te fatiguer : tu arrives frais et vif.",
        "how": "• Court, avec quelques efforts maîtrisés, puis rentre.\n• Ne cherche aucune performance : sors en te sentant bien.",
        "mistake": "Vouloir « tester ta forme » à quelques jours de l'objectif. Fais confiance au travail déjà fait.",
    },
    "cadence": {
        "name": "le travail de cadence",
        "why": "Il améliore ta fluidité de pédalage et ton efficacité, et te donne de l'aisance à haute cadence. Ton capteur de cadence te donne le chiffre.",
        "how": "• Pendant les accélérations, 100 à 110 tours par minute avec le même effort.\n• Reste souple dans les hanches, sans rebondir sur la selle.\n• Reviens ensuite à ta cadence naturelle.",
        "mistake": "Forcer sur le braquet pour aller plus vite : ici on tourne les jambes, on ne pousse pas plus fort.",
    },
    "sprints": {
        "name": "les sprints",
        "why": "Ils entretiennent la puissance explosive et le recrutement musculaire, sur des efforts si courts qu'ils fatiguent très peu.",
        "how": "• 10 secondes à fond, départ lancé ou en côte, puis 3 minutes de récupération complète.\n• Ta fréquence cardiaque n'aura pas le temps de monter : c'est normal.",
        "mistake": "Sprinter fatigué ou raide. Fais-le frais, avec un bon échauffement.",
    },
}

KIND_WORDS = [
    (("30/30", "pyramide", "vo2"), "vo2"), (("over-under", "over under", "overunder", "seuil"), "threshold"), (("sweet spot", "sweet", "tempo"), "tempo"),
    (("sortie longue", "longue"), "long"), (("recup", "recuperation"), "recovery"), (("cote", "cotes", "force"), "hills"),
    (("cadence",), "cadence"), (("sprint", "sprints"), "sprints"), (("affutage", "affuter"), "sharpen"), (("endurance", "zone 2"), "endurance"),
]


def kind_from_text(m: str) -> str | None:
    for words, kind in KIND_WORDS:
        if has(m, *words):
            return kind
    return None


def why_text(kind: str) -> str:
    p = PURPOSE[kind]
    return f"## À quoi sert {p['name']}\n{p['why']}"


def how_text(kind: str) -> str:
    p = PURPOSE[kind]
    return f"## Comment réussir {p['name']}\n{p['how']}\n\n❌ Erreur classique : {p['mistake']}"


def sick_reply() -> str:
    return (
        "Pas de sport tant que tu n'es pas rétabli, c'est la règle d'or. Quelques repères généraux (je ne suis pas médecin) :\n"
        "• **Symptômes seulement au-dessus du cou** (nez qui coule, gorge légèrement irritée) et pas de fièvre : une sortie très facile de 20 à 30 min en zone 1 est possible si tu te sens bien. Sinon, repos.\n"
        "• **Fièvre, courbatures, toux grasse, fatigue marquée, maux de ventre** : repos complet, aucune séance. Reprends seulement 1 à 2 jours après la disparition complète des symptômes, avec de l'endurance facile.\n"
        "• Gêne à la poitrine, essoufflement inhabituel, palpitations : arrête tout et consulte un médecin.\n"
        "Ne cherche pas à rattraper les séances manquées : le plan s'ajuste tout seul à la fin de la semaine."
    )


def motivation_reply(tone: str, name: str = "") -> str:
    base = {
        "encouraging": "Je te comprends, ça arrive à tout le monde, même aux plus motivés ! 💪 ",
        "direct": "Ça arrive. Voici ce qu'on fait : ",
        "analytical": "C'est un phénomène courant : la motivation fluctue, la routine tient. ",
        "kind": "C'est normal d'avoir des jours sans, sois indulgent avec toi-même. 🌱 ",
    }.get(tone, "")
    return (
        base + "\n• **La règle des 10 minutes** : enfile ta tenue et roule 10 minutes très facilement. Si au bout de 10 minutes tu n'as toujours pas envie, tu rentres, sans culpabilité. Dans 8 cas sur 10, tu continues.\n"
        "• Réduis l'objectif plutôt que de sauter la séance : 30 minutes de zone 2 valent mieux que rien.\n"
        "• Prépare ta tenue et tes bidons la veille, fixe une heure et un créneau.\n"
        "• Si ce manque d'envie dure plus de 1 à 2 semaines, accompagné de fatigue, c'est peut-être un signe de surcharge : parle-m'en, on allège le plan."
    )


def sleep_reply() -> str:
    return (
        "Le sommeil, c'est ton meilleur « dopage » légal : c'est pendant que tu dors que ton corps s'adapte à l'entraînement.\n"
        "• Vise **7 à 9 h** par nuit, avec des horaires réguliers (même à ±1 h le week-end).\n"
        "• Évite les écrans et la lumière vive 30 à 60 min avant de dormir, garde la chambre fraîche et sombre.\n"
        "• Caféine : pas après 14–15 h. Évite les gros repas et l'alcool le soir.\n"
        "• Après une grosse séance, ajoute si possible 30 à 60 min de sommeil.\n"
        "• Si tu dors moins de 6 h plusieurs nuits d'affilée, allège les séances dures de la semaine : tu progresseras plus en récupérant.\n"
        "Si tu as des troubles du sommeil persistants, parles-en à un médecin."
    )


def tired_reply(tsb_level: str, planned_kind: str | None, planned_title: str | None) -> str:
    lines = ["Écoute ton corps : la fatigue est une information, pas une faiblesse."]
    heavy = planned_kind in ("tempo", "threshold", "vo2", "hills", "sharpen")
    if tsb_level in ("surcharge", "charge"):
        lines.append("Les chiffres confirment : ta charge récente est élevée, il est logique que tu sois fatigué.")
    elif tsb_level in ("frais", "tres_frais"):
        lines.append("Pourtant tes chiffres de charge sont plutôt bons : la fatigue vient peut-être du sommeil, du stress ou de l'alimentation, plus que de l'entraînement.")
    if planned_title:
        if heavy:
            lines.append(f"Aujourd'hui tu as « {planned_title} », une séance d'intensité : si tes jambes sont lourdes ou ta fréquence cardiaque au repos est élevée de plus de 5–7 bpm, **remplace-la par de l'endurance facile en zone 2 (30 à 60 min)** ou par du repos. Mieux vaut sauter une séance dure que d'enchaîner une mauvaise séance.")
        else:
            lines.append(f"Aujourd'hui tu as « {planned_title} » : fais-la en restant strictement en zone 1-2, et raccourcis-la si besoin.")
    lines.append("Vérifie le trio **sommeil, repas, stress**. Si tu es épuisé plusieurs jours de suite, même au repos, ou si tu as de la fièvre, des douleurs ou un malaise : pas de sport et consulte.")
    return "\n".join(lines)
