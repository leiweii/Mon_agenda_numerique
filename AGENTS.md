# AGENTS.md — Guide de travail pour l'agent (Codex)

Ce fichier est lu automatiquement par Codex au début de chaque session. Il décrit le
projet, les règles à suivre, et l'état d'avancement réel des fonctionnalités.
**Codex : lis ce fichier en entier avant de commencer une tâche.**

---

## 0. Ta toute première tâche

Avant de coder quoi que ce soit, fais un **audit du repo** :
1. Parcours `backend/` et `frontend/src/` fichier par fichier.
2. Pour chaque fonctionnalité listée dans la section **"État d'avancement"** ci-dessous,
   vérifie si elle est réellement implémentée, partiellement implémentée, ou absente.
3. Mets à jour les cases `[ ]` / `[~]` / `[x]` de cette section en conséquence, et
   ajoute une courte note (fichier concerné, ce qu'il manque).
4. Ne modifie aucun autre fichier pendant cette tâche. Fais un commit séparé
   `docs: audit état du projet`.

Une fois cet audit fait, on travaille fonctionnalité par fonctionnalité (section 4).

---

## 1. Contexte du projet

**Mon Agenda Numérique** — application de gestion de tâches et d'agenda personnel.

- **Backend** : Python, Django, Django REST Framework, PostgreSQL, auth par token
- **Frontend** : React 18, Material-UI (MUI), React Router v6, Axios, Recharts, date-fns
- **Repo** : voir structure détaillée dans `README.md`

Objectif global : terminer les fonctionnalités listées dans le README (certaines sont
annoncées mais incomplètes ou absentes), et intégrer un pipeline de recommandations LLM
(section 5 de ce fichier).

---

## 2. Environnement & commandes

### Backend
```bash
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver      # http://localhost:8000
python manage.py test           # tests backend
```

### Frontend
```bash
cd frontend
npm install
npm start                       # http://localhost:3000
npm test                        # tests frontend
```

Variables d'environnement attendues dans `.env` (racine) : voir README section Installation.

---

## 3. Règles de travail pour l'agent

- **Une tâche = une fonctionnalité = un commit.** Ne pas mélanger plusieurs
  fonctionnalités dans un même commit/diff.
- **Toujours écrire ou mettre à jour les tests** correspondant au code touché
  (`python manage.py test` côté back, `npm test` côté front). Ne pas considérer une
  tâche terminée si les tests ne passent pas.
- **Ne pas casser l'existant** : si une modification touche un endpoint ou composant
  utilisé ailleurs, vérifier les usages avant de changer la signature.
- **Sécurité** : aucune clé API ou secret en dur dans le code. Tout passe par `.env` /
  `python-decouple` côté backend, jamais exposé côté React.
- **Style** : suivre les conventions déjà présentes dans le fichier édité (nommage,
  imports, structure des composants) plutôt que d'introduire un nouveau style.
- **En cas de doute** sur une décision produit (UX, priorité d'une fonctionnalité),
  ajouter une note dans le commit/PR plutôt que de deviner silencieusement.
- Après chaque tâche, mettre à jour la case correspondante dans la section
  "État d'avancement" (`[ ]` → `[~]` → `[x]`).

---

## 4. État d'avancement des fonctionnalités

> Légende : `[ ]` pas fait · `[~]` partiel/à finir · `[x]` fait et testé
> **À remplir par l'audit initial (section 0), puis tenir à jour après chaque tâche.**

### Tâches (CRUD)
- [~] Créer une tâche (titre, description, date d'échéance, priorité, catégorie)
  - Implémenté dans `backend/api/views.py` et `frontend/src/components/Taches/TacheForm.jsx`; tests métier et validation supplémentaire absents.
- [~] Modifier une tâche
  - `TacheViewSet` fournit la mise à jour et l'interface l'appelle depuis `TacheListe.jsx`; aucun test CRUD.
- [~] Supprimer une tâche
  - `TacheViewSet` fournit la suppression et `TacheCard.jsx` l'expose; aucun test CRUD.
- [~] Lister les tâches / filtrer par jour / semaine
  - Les endpoints et appels Dashboard existent dans `backend/api/views.py` et `Dashboard.jsx`; l'écran des tâches ne propose pas de filtres jour/semaine et aucun test.

### Personnalisation
- [~] Emoji + couleur par tâche
  - Champs modèle et sélecteurs dans `TacheForm.jsx` présents; validation et tests absents.
- [~] Catégories personnalisées (CRUD)
  - ViewSet et composants CRUD présents dans `backend/api/views.py` et `frontend/src/components/Categories/`; aucun test.
- [~] Système de priorités (4 niveaux)
  - Les quatre choix sont définis dans `backend/agenda/models.py` et affichés côté React; aucun test.

### Dashboard & statistiques
- [~] Total de tâches / taux de complétion
  - Calcul API et cartes Dashboard présents dans `backend/api/views.py` et `Dashboard.jsx`; aucun test.
- [~] Graphiques de priorités (Recharts)
  - Camembert implémenté dans `frontend/src/components/Statistiques/GraphiquesPriorite.jsx`; aucun test.
- [~] Endpoint `GET /api/taches/statistiques/`
  - Action DRF `statistiques` présente dans `backend/api/views.py`; aucun test d'endpoint.

### Recommandations
- [~] Endpoint `GET /api/taches/meilleur_moment/` (règles simples actuelles)
  - Action à règles simples présente dans `backend/api/views.py`; aucun test.
- [ ] Pipeline LLM (voir section 5)
  - Aucun service, endpoint ou composant LLM trouvé.

### Préférences & paramètres
- [~] Heures productives
  - Modèle et formulaire présents dans `backend/agenda/models.py` et `Parametres.jsx`; création front manquante dans `preferencesAPI` et aucun test.
- [~] Thème clair/sombre
  - Valeur enregistrable dans les préférences, mais le thème MUI fixe de `App.js` ne l'utilise pas; aucun test.
- [~] Notifications configurables
  - Interrupteur et champ de préférence présents, mais aucune notification réelle ni test.

### Auth
- [x] Login / logout / utilisateur courant (token auth)
  - Endpoints token, invalidation de session et contexte/formulaire React couverts par `backend/api/tests.py`, `AuthContext.test.jsx` et `Login.test.jsx`.

### Autres
- [~] Interface responsive (mobile/tablette/desktop)
  - Drawer et grilles responsives dans `App.js` et les composants; validation multi-format et tests absents.

---

## 5. Pipeline LLM (recommandations IA)

Objectif : remplacer/enrichir `GET /api/taches/meilleur_moment/` avec des
recommandations générées par LLM (priorisation, résumé hebdomadaire, détection de
surcharge), à partir des tâches/catégories/préférences existantes.

### 5.1 Config & sécurité
- [ ] `LLM_API_KEY` dans `.env`, jamais exposée côté React
  - Aucune configuration LLM trouvée.
- [ ] `LLM_API_KEY` chargée dans `backend/backend/settings.py` via `python-decouple`
  - `settings.py` charge uniquement la configuration de base de données.
- [ ] SDK installé (`pip install anthropic`) et ajouté à `requirements.txt`
  - `backend/requirements.txt` ne contient pas `anthropic`.

### 5.2 Service `backend/api/llm_service.py`
- [ ] `construire_prompt(taches, preferences)` — prompt structuré, réponse JSON stricte
  - Fichier `backend/api/llm_service.py` absent.
- [ ] Nettoyage/validation des données injectées (anti-injection, troncature)
  - Aucun service LLM trouvé.
- [ ] `appeler_llm(prompt)` — timeout + retries
  - Aucun service LLM trouvé.
- [ ] `parser_reponse(texte_llm)` — parsing JSON + fallback + logging si format invalide
  - Aucun service LLM trouvé.

### 5.3 Endpoint Django
- [ ] `RecommandationIAView` dans `backend/api/views.py`
  (données utilisateur → prompt → appel LLM → parsing → réponse)
  - Aucune vue IA dans `backend/api/views.py`.
- [ ] Route ajoutée dans `backend/api/urls.py`
  - Aucune route de recommandation IA.
- [ ] Fallback vers l'ancien système à règles si l'appel LLM échoue
  - Aucun appel LLM à sécuriser; l'ancien endpoint à règles reste indépendant.

### 5.4 Coût / performance
- [ ] Cache des résultats (recalcul 1x/jour ou si les tâches changent)
  - Aucun mécanisme de cache pour des recommandations IA.
- [ ] Rate limiting par utilisateur
  - Aucun mécanisme de limitation pour des recommandations IA.
- [ ] Logging des appels (prompt, durée, succès/échec)
  - Aucun appel LLM ni journalisation associée.

### 5.5 Frontend
- [ ] `frontend/src/components/RecommandationsIA.jsx`
  - Composant absent.
- [ ] Appel via `frontend/src/services/api.js`
  - Aucun client d'endpoint IA.
- [ ] État de chargement (skeleton/spinner)
  - Aucun composant IA.
- [ ] Gestion des erreurs (message clair si échec)
  - Aucun composant IA.
- [ ] Intégration dans le Dashboard
  - `Dashboard.jsx` n'utilise que `meilleur_moment` à règles simples.

### 5.6 Tests
- [ ] Backend : mock de l'appel LLM, test du parsing, test du fallback
  - `backend/api/tests.py` ne contient aucun test métier.
- [ ] Frontend : rendu du composant en loading / succès / erreur
  - Aucun composant IA; `App.test.js` est le test CRA par défaut.

### 5.7 Documentation
- [ ] README : nouvel endpoint + variable `LLM_API_KEY`
  - Aucun README racine et aucun document LLM trouvé.
- [ ] Format du prompt et de la réponse JSON documenté ici ou dans `/docs`
  - Aucun service, contrat JSON ou dossier de documentation LLM trouvé.

---

## 6. Points de vigilance (rappel)

- Clé API LLM uniquement côté backend
- Éviter les appels LLM à chaque chargement de page (cache !)
- Toujours prévoir un fallback si parsing/API échoue
- Latence perceptible côté LLM → toujours un état de chargement React
