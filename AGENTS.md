# AGENTS.md - Guide de reprise du projet

Ce fichier est le point d'entree pour un agent Codex ou pour une personne
qui decouvre le depot. Il doit rester court, vrai et actionnable. Les details
de conception longs vivent dans `docs/` ou `docs/superpowers/plans/`.

## 1. Projet en une minute

**Mon Agenda Numerique** est une application personnelle de gestion de taches.
Elle combine un backend Django REST, un frontend React/MUI et un module de
recommandations d'horaires avec appel Anthropic optionnel et repli local.

Le projet est fonctionnel en developpement local, mais il n'est pas pret pour
la production. Les principaux points non termines sont les statistiques de
compte reelles, l'alimentation automatique des habitudes, la configuration SMTP
de production et la configuration de deploiement.

Stack actuelle :

- Backend : Python, Django 6, Django REST Framework, PostgreSQL, token auth.
- Frontend : React 19, React Router 7, Material UI 7, Axios, Recharts, date-fns.
- IA : SDK `anthropic` cote Django, avec repli deterministe si aucune cle n'est disponible.

## 2. Carte rapide du code

- `backend/backend/settings.py` : configuration Django, base de donnees, CORS, apps.
- `backend/api/auth_backends.py` : authentification par e-mail ou nom d'utilisateur.
- `backend/api/authentication.py` : login, inscription, logout, utilisateur courant et reset de mot de passe.
- `backend/api/models.py` : taches, categories, preferences, statistiques, cache et journaux LLM.
- `backend/api/serializers.py` : contrats JSON exposes par l'API.
- `backend/api/views.py` : viewsets REST, statistiques, recommandations a regles et IA.
- `backend/api/llm_service.py` : prompt, appel Anthropic, parsing et validation de reponse.
- `backend/api/llm_performance.py` : cache, quota, journalisation et purge LLM.
- `backend/api/signals.py` : invalidation du cache de recommandation.
- `frontend/src/services/api.js` : client Axios et base URL locale.
- `frontend/src/context/AuthContext.jsx` : etat d'authentification React.
- `frontend/src/pages/` : pages principales (`Home`, `Login`, `Inscription`,
  `MotDePasseOublie`, `ReinitialiserMotDePasse`, `Parametres`).
- `frontend/src/components/Taches/` : liste, carte et formulaire de taches.
- `frontend/src/components/Categories/` : CRUD des categories.
- `frontend/src/components/Statistiques/` : dashboard et graphique de priorites.
- `frontend/src/components/RecommandationsIA.jsx` : carte de recommandation IA.
- `docs/llm-contract.md` : contrat prompt/reponse des recommandations.
- `docs/llm-cache-quota-logging.md` : architecture cache, quota et journalisation.
- `docs/superpowers/plans/2026-09-10-llm-cache-quota-logging.md` : plan de mise en oeuvre detaille du controle cache/quota/journaux.
- `docs/superpowers/specs/2026-09-10-authentification-complete-design.md` : conception de l'authentification complete.
- `docs/superpowers/plans/2026-09-10-authentification-complete.md` : plan d'execution de l'authentification complete.

## 3. Commandes utiles

Backend, depuis la racine du depot :

```bash
python -m venv venv
venv\Scripts\activate
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
python manage.py test
```

Frontend :

```bash
cd frontend
npm install
npm start
npm test -- --watchAll=false
```

Serveurs locaux attendus :

- API Django : `http://localhost:8000`
- Frontend React : `http://localhost:3000`
- Base API frontend actuelle : `http://localhost:8000/api/`

## 4. Maniere de travailler dans ce depot

- Une tache fonctionnelle doit correspondre a un lot/commit coherent. Ne pas
  melanger une fonctionnalite, une refonte et une correction sans lien.
- Avant de modifier une zone, lire les fichiers concernes et les tests deja
  presents. Suivre les conventions locales plutot qu'introduire un style neuf.
- Pour un changement complexe, ne pas dupliquer toute la conception dans ce
  fichier. Creer ou mettre a jour un document dans `docs/` ou
  `docs/superpowers/plans/`, puis mettre ici seulement le lien et l'etat resume.
- S'arreter et demander confirmation avant toute decision architecturale :
  changement de backend d'authentification, modification de modele de donnees,
  migration touchant des donnees existantes, ou choix qui contraint durablement
  les interfaces backend/frontend.
- La section **Etat reel actuel** doit etre mise a jour a chaque lot/commit
  termine et teste. Elle ne doit pas etre reservee aux audits ponctuels, sinon
  elle redevient obsolete comme un ancien README.
- Ajouter ou adapter les tests au meme moment que le comportement modifie.
  Avant de declarer un lot termine, executer les tests backend et frontend
  pertinents, ou expliquer clairement ce qui n'a pas pu etre lance.
- Ne jamais ajouter de secret dans Git, le frontend, les tests ou la
  documentation. Les cles LLM restent cote backend via l'environnement.
- Ne pas modifier les migrations, dependances ou code applicatif pour une tache
  purement documentaire.
- Pour les nouveaux composants MUI, preferer l'API MUI 7 (`size`) plutot que
  l'ancienne API Grid (`item`, `xs`, `sm`, `md`) encore presente dans certains
  composants.
- Proteger les changements utilisateur existants : ne pas annuler des fichiers
  modifies sans demande explicite.

## 5. Etat reel actuel

Legende : `[x]` implemente et couvert par les tests presents ; `[~]` partiel ou
avec limite connue ; `[ ]` absent.

### Authentification

- [x] Connexion par e-mail ou nom d'utilisateur, deconnexion et utilisateur
  courant par token. Fichiers principaux : `backend/api/auth_backends.py`,
  `backend/api/authentication.py`,
  `frontend/src/context/AuthContext.jsx`, `frontend/src/pages/Login.jsx`.
- [x] Inscription utilisateur par e-mail : `POST /api/auth/register/`, username
  interne genere automatiquement, validation Django du mot de passe,
  confirmation de mot de passe, token retourne et session ouverte cote frontend.
- [x] Limitation des tentatives d'authentification : quotas DRF pour inscription,
  login, demande de reset et confirmation de reset ; le frontend remonte les
  erreurs `429` via le champ `detail`.
- [~] Mot de passe oublie et reinitialisation : endpoints et ecrans implementes,
  lien avec token Django, confirmation de mot de passe et tests presents. En
  production, la configuration SMTP reelle reste a fournir par environnement.

### Taches et categories

- [x] CRUD des taches avec titre, description, echeance, priorite, categorie,
  couleur, emoji et etat complete.
- [x] Filtres "aujourd'hui" et semaine ISO via les actions API correspondantes.
- [x] CRUD des categories personnalisees, scope par utilisateur.
- [x] Suppression d'une categorie avec conservation des taches associees via
  categorie nulle.

### Preferences et interface

- [x] Preferences utilisateur persistantes : heures productives, theme clair/sombre
  et notifications.
- [x] Chargement du theme sauvegarde au demarrage, avec normalisation des anciennes
  valeurs `auto`.
- [~] Responsive partiel : `Home`, `Parametres` et `Dashboard` ont ete adaptes et
  testes ; `TacheForm.jsx` et les composants de categories utilisent encore
  l'ancienne API Grid MUI.
- [~] Statistiques de compte dans `Parametres.jsx` : valeurs de demonstration
  calculees dans le frontend, sans donnees API reelles.

### Dashboard et statistiques

- [x] Endpoint `GET /api/taches/statistiques/` avec total, taux de completion et
  repartition des priorites 1 a 4, zeros inclus.
- [x] Graphique Recharts des priorites integre au dashboard.

### Recommandations

- [~] `GET /api/taches/meilleur_moment/` existe et respecte le contrat
  `{heures_recommandees, message}`. Limite connue : les statistiques
  d'utilisation ne sont pas alimentees automatiquement lors de la completion
  normale d'une tache.
- [x] `GET /api/taches/recommandation_ia/` appelle le service LLM quand c'est
  possible et garantit le meme contrat JSON en cas de succes, d'erreur ou de
  repli local.
- [x] Cache persistant 24 h, quota quotidien par utilisateur, journalisation
  pseudonymisee et purge probabiliste des anciens journaux. Details dans
  `docs/llm-cache-quota-logging.md` et plan d'execution dans
  `docs/superpowers/plans/2026-09-10-llm-cache-quota-logging.md`.
- [x] Frontend `RecommandationsIA.jsx` avec etats chargement, succes, erreur et
  action de nouvel essai.

### Configuration et production

- [~] Configuration locale fonctionnelle avec PostgreSQL, CORS local et URL Axios
  locale.
- [~] Non pret production : `DEBUG=True`, `SECRET_KEY` codee en dur, URL API
  locale et configuration SMTP doivent etre externalises ou securises avant
  deploiement.

## 6. Contrats a ne pas casser

Reponse de recommandation, quelle que soit la source :

```json
{
  "heures_recommandees": [9, 14],
  "message": "Une recommandation concise."
}
```

Routes API principales, toutes prefixees par `/api/` :

- `POST /auth/login/`, `POST /auth/register/`, `POST /auth/logout/`, `GET /auth/user/`
- `POST /auth/mot-de-passe-oublie/`, `POST /auth/reinitialiser-mot-de-passe/`
- `/taches/`, `/taches/{id}/`, `/taches/aujourd_hui/`, `/taches/cette_semaine/`
- `/taches/statistiques/`, `/taches/meilleur_moment/`, `/taches/recommandation_ia/`
- `/categories/`, `/categories/{id}/`
- `/preferences/`, `/preferences/{id}/`

## 7. Verification attendue

Pour un changement backend :

```bash
cd backend
python manage.py test
```

Pour un changement frontend :

```bash
cd frontend
npm test -- --watchAll=false
```

Pour un changement documentaire seul, relire le rendu Markdown et verifier que
les chemins cites existent. Les tests applicatifs ne sont pas obligatoires si
aucun comportement, dependance ou contrat n'a change.
