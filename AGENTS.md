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
- [x] Créer une tâche (titre, description, date d'échéance, priorité, catégorie)
  - Création, validation de catégorie et erreur de formulaire couvertes par `backend/api/tests.py` et `TacheForm.test.jsx`.
- [x] Modifier une tâche
  - Mise à jour protégée par utilisateur testée dans `backend/api/tests.py`; les erreurs restent visibles dans `TacheForm.jsx`.
- [x] Supprimer une tâche
  - Suppression et isolation par utilisateur couvertes dans `backend/api/tests.py`.
- [x] Lister les tâches / filtrer par jour / semaine
  - `/api/taches/aujourd_hui/` et `/api/taches/cette_semaine/` filtrent la date locale et la semaine ISO (lundi-dimanche) ; le sélecteur de `TacheListe.jsx` et ses tests couvrent les deux vues.

### Personnalisation
- [x] Emoji + couleur par tâche
  - Validation `#RRGGBB`, sélecteurs emoji/palette/color picker et persistance API couverts par les tests.
- [x] Catégories personnalisées (CRUD)
  - CRUD isolé par utilisateur, formulaire React et attribution à une tâche couverts par les tests ; supprimer une catégorie conserve les tâches avec `categorie=null`.
- [x] Système de priorités (4 niveaux)
  - Les niveaux Basse, Moyenne, Haute et Urgente sont validés par Django, sélectionnables dans le formulaire et affichés par un chip coloré testé.

### Dashboard & statistiques
- [x] Total de tâches / taux de complétion
  - Les calculs isolés par utilisateur et les cartes Dashboard sont couverts par les tests backend et frontend.
- [x] Graphiques de priorités (Recharts)
  - `GraphiquesPriorite.jsx` reçoit les quatre priorités normalisées et son rendu/état vide sont testés.
- [x] Endpoint `GET /api/taches/statistiques/`
  - L'action retourne total, complétées, en cours, taux et `[{'priorite': 1..4, 'count': n}]`, y compris les zéros.

### Recommandations
- [x] Endpoint `GET /api/taches/meilleur_moment/` (règles simples actuelles)
  - Retourne pour l'utilisateur connecté jusqu'à trois heures de complétion les plus fréquentes (départage par heure croissante), ou une liste vide; contrat et accès token couverts par les tests.
- [ ] Pipeline LLM (voir section 5)
  - Aucun service, endpoint ou composant LLM trouvé.

### Préférences & paramètres
- [x] Heures productives
  - `PreferenceUtilisateur` valide une plage début/fin cohérente; création, mise à jour et formulaire sont couverts par les tests.
- [x] Thème clair/sombre
  - Les seuls thèmes `clair` et `sombre` sont validés, `auto` existant est migré vers `clair`, et le thème MUI est chargé au démarrage puis appliqué après sauvegarde.
- [x] Notifications configurables
  - L'interrupteur est persisté via `/api/preferences/` et couvert par les tests de création du formulaire et de l'endpoint.

### Auth
- [x] Login / logout / utilisateur courant (token auth)
  - Endpoints token, invalidation de session et contexte/formulaire React couverts par `backend/api/tests.py`, `AuthContext.test.jsx` et `Login.test.jsx`.

### Autres
- [x] Interface responsive (mobile/tablette/desktop)
  - `Home.jsx`, `Parametres.jsx` et `Dashboard.jsx` utilisent l'API Grid de MUI 7.3.7 (`size` pour xs/sm/md), testée pour mobile, tablette et desktop; le padding du layout est adapté au mobile.
  - Hors périmètre : `components/Taches/` et `components/Categories/` utilisent encore l'ancienne API Grid (`item`, `xs`, `sm`, `md`) supprimée par MUI v7 et devront être migrés dans une tâche dédiée.

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
  - Contrat de sortie obligatoire, pour la réponse LLM comme pour le fallback : `{"heures_recommandees": [heures], "message": "texte"}`.
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
