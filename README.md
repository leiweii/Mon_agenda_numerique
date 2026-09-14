# Mon Agenda Numérique

Application web personnelle pour organiser ses tâches, suivre ses candidatures et obtenir des recommandations d'horaires de travail.

> Projet personnel en développement : fonctionnel en local, mais pas encore configuré pour un usage en production.

## Pourquoi ce projet ?

J'ai choisi ce projet parce qu'il répond à un besoin personnel réel : mieux organiser mes tâches et mon suivi de candidatures. C'était aussi un bon exercice full-stack pour travailler Django REST Framework, React, l'authentification, les tests et une première intégration d'IA.

## Sommaire

- [Pourquoi ce projet ?](#pourquoi-ce-projet-)
- [Fonctionnalités](#fonctionnalités)
- [Stack technique](#stack-technique)
- [Installation et lancement](#installation-et-lancement)
- [Structure du projet](#structure-du-projet)
- [Routes API](#routes-api)
- [Limites connues et pistes d'amélioration](#limites-connues-et-pistes-damélioration)
- [Tests](#tests)
- [Captures d'écran](#captures-décran)

## Fonctionnalités

### Authentification

- Inscription utilisateur par e-mail avec validation Django du mot de passe.
- Connexion par e-mail ou nom d'utilisateur.
- Session frontend basée sur un token DRF stocké côté client.
- Déconnexion avec suppression du token courant côté backend.
- Parcours mot de passe oublié avec envoi d'un lien par e-mail.
- Réinitialisation du mot de passe avec `uid`, `token`, nouveau mot de passe et confirmation.

### Tâches

- Création, consultation, modification et suppression de tâches.
- Champs disponibles : titre, description, date d'échéance, priorité, couleur, emoji, état complété et catégorie.
- Filtrage des tâches du jour.
- Filtrage des tâches de la semaine ISO courante.
- Priorités de 1 à 4 : basse, moyenne, haute, urgente.
- Données isolées par utilisateur authentifié.

### Catégories

- Création, modification et suppression de catégories personnalisées.
- Association d'une couleur et d'un emoji à chaque catégorie.
- Catégories limitées à l'utilisateur connecté.
- Suppression d'une catégorie sans suppression des tâches associées : les tâches conservent une catégorie vide.

### Tableau de bord

- Affichage du nombre total de tâches.
- Affichage des tâches complétées et en cours.
- Calcul du taux de complétion.
- Répartition des tâches par priorité, avec les priorités sans tâche incluses à zéro.
- Graphique Recharts pour visualiser les priorités.

### Recommandations IA

- Endpoint de recommandation d'horaires via Anthropic lorsqu'une clé API backend est disponible.
- Repli local déterministe lorsque le LLM est indisponible, invalide ou absent.
- Cache persistant des recommandations pendant 24 heures.
- Quota quotidien par utilisateur pour limiter les appels LLM.
- Journalisation pseudonymisée des appels LLM, sans stockage du contenu brut du prompt.
- Contrat de réponse stable pour le frontend :

```json
{
  "heures_recommandees": [9, 14],
  "message": "Une recommandation concise."
}
```

### Suivi de candidatures

- Création, consultation, modification et suppression de candidatures.
- Import depuis une URL d'offre d'emploi avec normalisation de l'URL.
- Détection des doublons par utilisateur avant tout nouvel import.
- Extraction automatique du titre et de la description depuis les métadonnées Open Graph ou le HTML nettoyé.
- Repli LLM pour analyser le HTML récupéré lorsque le scraping classique ne suffit pas.
- Champs de suivi : titre, entreprise, lieu, mode de travail, description, type de poste, statut, canal source, tags, favori, archivage, CV utilisé, date limite, date de relance et notes.
- Statuts disponibles : à postuler, postulé, entretien, refusé, accepté.
- Types de poste disponibles : stage, alternance, CDI, CDD, freelance, autre.
- Canaux disponibles : LinkedIn, Indeed, Welcome to the Jungle, site de l'entreprise, cooptation/réseau, autre.
- Filtres par recherche, statut, type de poste, canal, tags, favori, archives, date d'ajout, échéance sous 7 jours, relance due et tri.
- Archives masquées par défaut.
- Vue liste groupée par statut.
- Vue Kanban avec déplacement des candidatures entre statuts.
- Page détail pour chaque candidature.
- Historique d'actions par candidature : candidature envoyée, relance, entretiens, test technique, offre reçue, réponse négative et note libre.
- Export CSV des candidatures en respectant les filtres actifs.

## Stack technique

| Domaine | Technologies |
| --- | --- |
| Backend | Python, Django 6.0, Django REST Framework 3.16, PostgreSQL, authentification par token DRF, django-cors-headers, python-decouple |
| Frontend | React 19, React Router 7, Material UI 7, Axios, Recharts, date-fns, Create React App |
| IA | SDK Anthropic côté Django, cache applicatif, quotas journaliers, journalisation pseudonymisée, repli local sans clé API |

## Installation et lancement

### Prérequis

- Python 3
- PostgreSQL
- Node.js
- npm

### Backend

Depuis la racine du dépôt, créer et activer un environnement virtuel :

```bash
python -m venv venv
venv\Scripts\activate
```

Installer les dépendances backend :

```bash
cd backend
pip install -r requirements.txt
```

Créer un fichier `backend/.env` avec la configuration locale :

```env
DB_NAME=mon_agenda
DB_USER=postgres
DB_PASSWORD=mot_de_passe_postgres
DB_HOST=localhost
DB_PORT=5432

FRONTEND_URL=http://localhost:3000

# Facultatif : sans clé, l'application utilise le repli local.
LLM_API_KEY=cle_anthropic

# Facultatif : par défaut, Django écrit les e-mails dans la console.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@monagenda.local

# Facultatif : quota LLM dédié aux imports de candidatures.
CANDIDATURE_LLM_DAILY_LIMIT=10
```

Appliquer les migrations :

```bash
python manage.py migrate
```

Si la base locale n'a pas encore reçu les dernières migrations du projet, cette commande les applique avant le lancement du serveur.

Lancer l'API Django :

```bash
python manage.py runserver
```

L'API locale est disponible sur :

```text
http://localhost:8000
```

### Frontend

Dans un second terminal, installer les dépendances frontend :

```bash
cd frontend
npm install
```

Lancer l'application React :

```bash
npm start
```

L'interface locale est disponible sur :

```text
http://localhost:3000
```

Le client frontend appelle actuellement l'API à cette adresse :

```text
http://localhost:8000/api/
```

## Structure du projet

```text
mon_agenda/
├── backend/
│   ├── backend/          # Configuration Django
│   ├── agenda/           # Tâches, catégories, préférences, statistiques
│   └── api/              # API REST, auth, candidatures, LLM, tests
├── docs/                 # Contrats LLM et notes de conception
├── AGENTS.md             # État réel du projet et consignes de reprise
├── README.md
└── frontend/
    └── src/
        ├── components/   # UI par domaine : tâches, catégories, stats, candidatures
        ├── pages/        # Pages React principales
        ├── context/      # État d'authentification
        └── services/     # Client API et gestion d'erreurs
```

Le module de suivi de candidatures se trouve principalement dans `backend/api/` côté API et dans `frontend/src/pages/Candidatures.jsx`, `frontend/src/pages/CandidatureDetail.jsx` et `frontend/src/components/Candidatures/` côté interface.

## Routes API

Toutes les routes applicatives sont préfixées par `/api/`.

| Méthode | Route | Description |
| --- | --- | --- |
| POST | `/api/auth/login/` | Connexion par e-mail ou nom d'utilisateur, avec création d'un token |
| POST | `/api/auth/register/` | Inscription par e-mail, validation du mot de passe et ouverture de session |
| POST | `/api/auth/logout/` | Suppression du token de l'utilisateur connecté |
| GET | `/api/auth/user/` | Récupération de l'utilisateur connecté |
| POST | `/api/auth/mot-de-passe-oublie/` | Demande d'e-mail de réinitialisation de mot de passe |
| POST | `/api/auth/reinitialiser-mot-de-passe/` | Confirmation de réinitialisation avec `uid`, `token` et nouveau mot de passe |
| GET, POST | `/api/taches/` | Liste ou création des tâches |
| GET, PUT, PATCH, DELETE | `/api/taches/{id}/` | Détail, modification ou suppression d'une tâche |
| GET | `/api/taches/aujourd_hui/` | Tâches dont l'échéance est aujourd'hui |
| GET | `/api/taches/cette_semaine/` | Tâches de la semaine ISO courante |
| GET | `/api/taches/statistiques/` | Statistiques de tâches pour le tableau de bord |
| GET | `/api/taches/meilleur_moment/` | Recommandation basée sur les statistiques d'utilisation disponibles |
| GET | `/api/taches/recommandation_ia/` | Recommandation LLM avec cache, quota et repli local |
| GET, POST | `/api/categories/` | Liste ou création des catégories |
| GET, PUT, PATCH, DELETE | `/api/categories/{id}/` | Détail, modification ou suppression d'une catégorie |
| GET, POST | `/api/preferences/` | Liste ou création des préférences utilisateur |
| GET, PUT, PATCH, DELETE | `/api/preferences/{id}/` | Détail, modification ou suppression des préférences |
| GET, POST | `/api/candidatures/` | Liste filtrable ou création des candidatures |
| GET, PUT, PATCH, DELETE | `/api/candidatures/{id}/` | Détail, modification ou suppression d'une candidature |
| POST | `/api/candidatures/import_url/` | Analyse d'une URL d'offre, détection des doublons et préremplissage du formulaire |
| GET | `/api/candidatures/export_csv/` | Export CSV des candidatures en respectant les filtres actifs |
| PATCH | `/api/candidatures/{id}/archiver/` | Archivage d'une candidature |
| GET, POST | `/api/candidatures/{id}/actions/` | Liste ou création des actions liées à une candidature |
| GET, PUT, PATCH, DELETE | `/api/candidatures/{id}/actions/{action_id}/` | Détail, modification ou suppression d'une action de candidature |

L'administration Django reste disponible sur :

```text
/admin/
```

## Limites connues et pistes d'amélioration

- Préparer la configuration de production : externalisation de la `SECRET_KEY`, désactivation de `DEBUG`, gestion des hôtes autorisés, CORS de production et configuration de déploiement.
- Finaliser la configuration SMTP réelle pour les e-mails de réinitialisation de mot de passe hors environnement local.
- Remplacer les statistiques de démonstration de la page Paramètres par des données calculées côté API.
- Alimenter automatiquement les statistiques d'utilisation lors de la complétion normale des tâches, afin d'améliorer la recommandation locale du meilleur moment.
- Poursuivre l'harmonisation responsive de certains formulaires encore basés sur d'anciens usages de Grid MUI.

## Tests

### Backend

Depuis la racine du dépôt :

```bash
cd backend
python manage.py test
```

### Frontend

Depuis la racine du dépôt :

```bash
cd frontend
npm test -- --watchAll=false
```

Le script de test frontend utilise l'exécution en série via `--runInBand`, configurée dans `package.json`, pour limiter les timeouts liés à JSDOM et Material UI.

## Captures d'écran

*(Captures d'écran à venir)*
