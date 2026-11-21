---
title: Nexus Coach
emoji: 🚴
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# NEXUS COACH : le coach de VéloCoach (Python)

Un service Python (FastAPI) qui connaît ton profil de coach, ton plan, tes sorties Strava et ta forme, et qui répond à tes questions.
Il tourne en ligne, donc **il marche même quand ton PC est éteint**.

## Ce qu'il fait
- `POST /chat` : tu poses une question, il répond. Il garde l'historique de la conversation.
- `GET /brief` : ton point du jour (séance, forme, phase du plan).
- `GET /context` : résumé de ce qu'il sait de toi (pour vérifier que tout est branché).
- `GET /health` : état du service.

Il répond **sans aucune IA externe** grâce à des règles expertes basées sur tes données (séance du jour, semaine, forme, zones, bilan,
objectif, séances ratées, douleur, nutrition de base). Une IA gratuite peut être ajoutée pour les questions ouvertes (voir plus bas).

## Sécurité
- Chaque requête porte **ton jeton de connexion Supabase**. Le service lit tes données avec ce jeton : les règles de sécurité de la base
  (RLS) s'appliquent, donc il ne peut voir que tes propres données. Il n'a **jamais** la clé `service_role`.
- Douleur, blessure, malaise : réponse prudente fixe (pas de diagnostic, pas d'intensité, urgence si symptômes graves). Jamais confiée à une IA.
- Le code de ce dossier ne contient aucun secret. Les clés se mettent dans les « secrets » de l'hébergeur.

## Rester 100 % gratuit : la règle d'or
Aucun service de ce projet n'exige de carte bancaire. **N'en renseigne jamais** et ne choisis jamais un plan payant :
- **Supabase** : plan **Free** (500 Mo de base). Un projet inactif plus d'une semaine est mis en pause, tu le réactives en un clic.
- **Strava** : l'API est gratuite pour un usage personnel.
- **Expo Go** : gratuit. Ne lance jamais de build EAS ni de compte Apple Developer (99 $/an) : ils ne sont pas nécessaires.
- **Gemini** (IA, optionnelle) : crée ta clé dans Google AI Studio **sans activer la facturation** sur le projet Google Cloud associé.
  Sans facturation, un dépassement de quota donne une erreur (le coach répond alors avec ses règles), pas une facture.
- **Hébergement du coach** : choisis uniquement l'instance **Free** / « CPU basic ».
Si une limite gratuite est atteinte, le service ralentit ou s'arrête : il ne facture pas.

## Déployer gratuitement sur Render (recommandé)
Render propose un service web **gratuit** qui exécute directement ce dossier (il lit le `Dockerfile`).
1. Mets ce dossier sur **GitHub** (compte gratuit, dépôt **public** ou privé). Le fichier `.env`, `.venv` et `tests` sont déjà ignorés.
2. Crée un compte gratuit sur render.com (connexion avec GitHub) → **New → Blueprint** → choisis ton dépôt : Render lit `render.yaml`.
   Vérifie que le plan affiché est **Free**.
3. Saisis les variables demandées : `SUPABASE_URL`, `SUPABASE_ANON_KEY` (clé publique, jamais `service_role`) et, si tu veux l'IA, `GEMINI_API_KEY`.
4. Après 3 à 5 minutes, ton adresse est `https://nexus-coach-xxxx.onrender.com`. Teste `…/health` dans un navigateur.
5. Mets-la dans `EXPO_PUBLIC_COACH_URL` du `.env` de l'app, puis relance `npx expo start -c`.

Une instance gratuite s'endort après 15 minutes sans appel et met environ une minute à se réveiller au premier message
(l'app affiche « Le coach se réveille… »). Render offre 750 heures par mois d'instance gratuite.

## Alternative : Hugging Face Spaces
⚠️ En 2026, des utilisateurs signalent que le matériel gratuit « CPU basic » peut être limité ou demander un abonnement Pro. Vérifie
sur huggingface.co/pricing avant de t'y fier. Si ça ne marche pas gratuitement, utilise Render.
1. Crée un compte gratuit sur huggingface.co.
2. **New Space** → nom `nexus-coach` → SDK **Docker** (modèle « Blank ») → matériel **CPU basic (gratuit)** → visibilité **Public**
   (le code sera visible, mais il ne contient aucun secret et chaque appel exige ta connexion).
3. Dans l'onglet **Files** du Space : **Add file → Upload files** et glisse ces éléments de ce dossier : `Dockerfile`, `README.md`,
   `requirements.txt` et le dossier `app`. (Ne mets pas `.venv`, `tests`, `.env`.)
4. Onglet **Settings → Variables and secrets** → ajoute en **Secrets** :
   - `SUPABASE_URL` : l'adresse de ton projet Supabase (`https://xxxx.supabase.co`)
   - `SUPABASE_ANON_KEY` : ta clé publique `anon` / `publishable` (la même que dans l'app, jamais `service_role`)
   - (optionnel) `COACH_TZ` : `Europe/Paris` (valeur par défaut)
5. Le Space se construit (2 à 3 minutes). Son adresse est `https://<ton-pseudo>-nexus-coach.hf.space`.
   Teste `https://…hf.space/health` dans un navigateur : tu dois voir `{"ok":true,...}`.
6. Dans le fichier `.env` de l'app : `EXPO_PUBLIC_COACH_URL=https://<ton-pseudo>-nexus-coach.hf.space`, puis relance `npx expo start -c`.

Un Space gratuit s'endort après une longue période sans utilisation et se réveille tout seul à la première requête
(compte environ une minute : l'app l'affiche). Il peut aussi redémarrer de temps en temps. Les limites exactes sont à vérifier sur Hugging Face.

## Ajouter une IA gratuite (optionnel)
Sans IA, le coach répond avec ses règles. Pour qu'il comprenne des questions libres, tu peux ajouter un fournisseur **gratuit** :
- **Google Gemini** : crée une clé sur aistudio.google.com, puis ajoute le secret `GEMINI_API_KEY`
  (modèle réglable avec `GEMINI_MODEL`, par défaut `gemini-2.5-flash`). Les quotas gratuits changent : vérifie-les dans AI Studio.
- **Autre fournisseur compatible OpenAI** (Groq, OpenRouter…) : secrets `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.
- `COACH_LLM=none` force le mode sans IA.

⚠️ **Confidentialité** : quand une IA est branchée, un résumé de ton dossier (profil sportif, plan, sorties, forme, sans email, prénom
ni date de naissance exacte) est envoyé au fournisseur pour répondre. Lis ses conditions : les offres gratuites peuvent utiliser les
données pour s'améliorer. Si ça te gêne, ne branche aucune IA.

## Tester sur ton PC
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
powershell -File run-local.ps1      (lit l'URL et la clé Supabase dans ..\velocoach\.env)
```
