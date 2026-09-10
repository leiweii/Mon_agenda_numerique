# AGENTS.md - Guide de travail

## 1. Contexte et stack

**Mon Agenda Numérique** est une application personnelle de gestion de tâches.
Le projet est en développement ; l'état ci-dessous est issu du code présent dans
`backend/` et `frontend/src/`, et non des annonces antérieures.

- Backend : Python, Django 6, Django REST Framework, PostgreSQL, authentification par token.
- Frontend : React 19, React Router 7, Material UI 7, Axios, Recharts et date-fns.
- Recommandations : SDK Anthropic côté Django, avec repli local déterministe.

## 2. Commandes de développement

### Backend

Depuis la racine du dépôt :

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
python manage.py test
```

Le serveur écoute sur `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm start
npm test -- --watchAll=false
```

Le serveur de développement React écoute normalement sur `http://localhost:3000`.

## 3. Règles de travail pour un agent IA

- Une tâche fonctionnelle correspond à un commit isolé. Ne pas mélanger des refontes sans lien.
- Écrire ou adapter les tests concernés et exécuter `python manage.py test` ainsi que `npm test` avant de déclarer une tâche terminée.
- Ne jamais ajouter de secret dans le code, dans le frontend ou dans Git. Les clés passent par l'environnement et restent côté backend.
- Respecter les conventions, le nommage et les bibliothèques déjà employés dans le fichier modifié. Pour les nouveaux composants MUI, employer l'API MUI 7 (`size`) plutôt que l'ancienne API `item xs` encore visible dans certains formulaires.
- Ne pas modifier les migrations, dépendances ou code applicatif pour une tâche de documentation.
- Mettre à jour l'état ci-dessous après une évolution vérifiée par les tests.

## 4. État d'avancement

Légende : `[ ]` absent ; `[~]` partiel ou avec limite connue ; `[x]` implémenté et couvert par les tests présents.

### Authentification

- [x] Connexion, déconnexion et utilisateur courant par token : `api/authentication.py`, `AuthContext.jsx` et `Login.jsx` sont implémentés et testés.
- [x] Inscription utilisateur : `POST /api/auth/register/`, formulaire e-mail sans username visible, connexion automatique, confirmation, validation des mots de passe Django, normalisation et génération de username interne avec collision gérée sont implémentés et testés.
- [x] Connexion e-mail ou username : un même champ `identifier` accepte les comptes existants par username et les nouveaux comptes par e-mail ; les erreurs restent génériques et le quota est de cinq tentatives anonymes par quinze minutes.
- [x] Mot de passe oublié et réinitialisation : les routes `mot-de-passe-oublie` et `reinitialiser-mot-de-passe` utilisent les tokens Django, un message de demande générique, les validateurs Django et les quotas IP/e-mail configurés ; les formulaires et tests React correspondants sont présents.

### Tâches

- [x] CRUD des tâches : titre, description, échéance, priorité, catégorie, couleur, emoji et état complété sont gérés par `TacheViewSet` et les composants `Taches/`.
- [x] Listes générale, du jour et de la semaine ISO : actions `aujourd_hui` et `cette_semaine`, filtres correspondants dans `TacheListe.jsx`.
- [x] Catégories personnalisées : CRUD utilisateur-scopé ; supprimer une catégorie conserve les tâches avec une catégorie nulle (`SET_NULL`).
- [x] Priorités à quatre niveaux et affichage visuel : modèle, sérialiseur, formulaire et cartes de tâche.
- [x] Emoji et couleur par tâche : validation de couleur hexadécimale côté backend et sélecteurs dans le formulaire.

### Préférences et interface

- [x] Préférences utilisateur : heures productives, thème clair/sombre et notifications sont persistés et modifiables depuis `Parametres.jsx`.
- [x] Thème initial : l'application charge la préférence sauvegardée au démarrage ; les anciennes valeurs `auto` sont normalisées par migration.
- [~] Responsive : `Home`, `Parametres` et `Dashboard` utilisent les breakpoints MUI 7 et ont des tests dédiés ; `TacheForm.jsx` et les composants de catégories utilisent encore l'ancienne API Grid (`item`, `xs`, `sm`, `md`), qui produit des avertissements sous MUI 7.
- [~] Statistiques de compte dans les paramètres : les trois compteurs sont calculés aléatoirement dans le frontend, sans données API réelles.

### Dashboard et statistiques

- [x] Total, taux de complétion et répartition par priorité : endpoint `GET /api/taches/statistiques/`, avec les quatre priorités 1 a 4 y compris les zéros.
- [x] Graphique de priorités : `GraphiquesPriorite.jsx` utilise Recharts et est intégré au dashboard.

### Recommandations à règles

- [~] `GET /api/taches/meilleur_moment/` : l'endpoint et son contrat `{heures_recommandees, message}` existent et sont testés ; aucune logique applicative n'enregistre automatiquement les `StatistiqueUtilisation` lors de la complétion d'une tâche, donc les données d'habitudes ne sont pas alimentées en usage normal.

### Configuration de déploiement

- [~] Configuration de développement fonctionnelle : PostgreSQL, CORS local et URL Axios locale sont codés pour l'environnement local. `DEBUG=True`, une `SECRET_KEY` codée en dur et l'URL API `localhost` empêchent de qualifier cette configuration de prête pour la production.

## 5. Pipeline de recommandations LLM

Le contrat de sortie, commun au LLM et au repli à règles, est toujours :

```json
{
  "heures_recommandees": [9, 14],
  "message": "Une recommandation concise."
}
```

### Configuration

- [x] `LLM_API_KEY` est lue côté Django avec `python-decouple` ; elle n'est pas exposée au frontend.
- [x] Le SDK `anthropic` est présent dans `backend/requirements.txt`.
- [~] Une clé réelle reste nécessaire dans l'environnement pour appeler Anthropic ; sans elle, l'API utilise le repli local.

### Service

- [x] `api/llm_service.py` construit un prompt structuré, nettoie et tronque les données utilisateur, impose du JSON et valide la réponse.
- [x] L'appel Anthropic possède un délai, deux tentatives pour les erreurs transitoires, un modèle par défaut et une limite de 256 tokens.
- [x] Les erreurs techniques ou de format renvoient `None` et sont journalisées sans contenu de prompt ni de réponse.

### Endpoint

- [x] `GET /api/taches/recommandation_ia/` récupère les tâches et préférences de l'utilisateur, appelle le service puis garantit le contrat JSON.
- [x] En cas d'absence de clé, d'échec LLM ou de réponse invalide, l'endpoint utilise `meilleur_moment` comme repli.

### Cache, quota et journalisation

- [x] Cache persistant en base, clé dérivée de l'utilisateur, des tâches et préférences, TTL de 24 heures ; invalidation par signaux à chaque modification de tâche ou préférence.
- [x] Quota de dix appels externes Anthropic par utilisateur et par jour calendaire ; au-delà, dernière réponse en cache ou repli local.
- [x] Journalisation en base de métadonnées pseudonymisées uniquement, avec purge probabiliste des entrées de plus de trente jours.

### Frontend

- [x] `RecommandationsIA.jsx` appelle l'API, affiche un skeleton de chargement, le résultat et une erreur avec possibilité de réessayer ; il est intégré à `Dashboard`.

### Tests

- [x] Tests backend pour le service, le parsing, le cache, le quota, l'endpoint et les replis.
- [x] Tests frontend pour les états chargement, succès et erreur du composant de recommandations.

### Documentation

- [x] Le contrat du prompt et de la réponse est décrit dans `docs/llm-contract.md`.
- [x] L'architecture cache/quota/journalisation est décrite dans `docs/llm-cache-quota-logging.md`.
