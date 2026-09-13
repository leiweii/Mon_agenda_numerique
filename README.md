# Mon Agenda Numérique

Application personnelle de gestion de tâches avec tableau de bord, catégories,
préférences et recommandations d'horaires. Le projet est **en développement** :
les fonctions décrites ci-dessous correspondent au code actuel, mais la
configuration n'est pas encore prête pour un déploiement de production.

## Fonctionnalités actuelles

- Authentification par token : inscription par e-mail, connexion par e-mail ou username, déconnexion, récupération du compte et utilisateur courant.
- Création, modification, suppression et filtrage des tâches par jour ou semaine ISO.
- Catégories personnalisées, couleurs, emoji et quatre niveaux de priorité.
- Tableau de bord avec statistiques et graphique Recharts des priorités.
- Préférences utilisateur : heures productives, thème clair/sombre et notifications.
- Recommandations via Anthropic lorsqu'une clé est disponible, avec cache, quota et repli à règles locales.

Limites connues : les statistiques de compte de la page Paramètres sont des valeurs de démonstration, et les habitudes utilisées
par la recommandation à règles ne sont pas enregistrées automatiquement lors de
la complétion des tâches. Voir [AGENTS.md](AGENTS.md) pour l'état détaillé.

## Stack technique

### Backend

- Python et Django 6.0
- Django REST Framework 3.16
- PostgreSQL
- Authentification par token DRF
- `python-decouple` et SDK `anthropic`

### Frontend

- React 19.2
- React Router 7.13
- Material UI 7.3
- Axios, Recharts et date-fns
- Create React App (`react-scripts`)

## Installation

### Prérequis

- Python 3 et PostgreSQL
- Node.js et npm

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
```

Créer `backend/.env` avec les variables réellement lues par `backend/settings.py` :

```env
DB_NAME=mon_agenda
DB_USER=postgres
DB_PASSWORD=mot_de_passe_postgres
DB_HOST=localhost
DB_PORT=5432

# Facultative : sans elle, les recommandations IA utilisent le repli local.
LLM_API_KEY=cle_anthropic

# Adresse publique du frontend utilisée dans les liens de réinitialisation.
FRONTEND_URL=http://localhost:3000

# En développement, la valeur par défaut est le backend console Django.
# Pour SMTP, définir ces variables dans l'environnement, jamais dans le frontend.
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=utilisateur_smtp
EMAIL_HOST_PASSWORD=mot_de_passe_smtp
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@example.com
```

`LLM_API_KEY` doit rester uniquement côté backend et ne doit jamais être placée
dans un fichier du frontend. Le projet lit actuellement une `SECRET_KEY` Django
codée en dur et active `DEBUG`; ne pas le déployer tel quel en production.

Appliquer les migrations et lancer le serveur :

```bash
python manage.py migrate
python manage.py runserver
```

L'API est disponible sur `http://localhost:8000`.

### Frontend

Dans un autre terminal :

```bash
cd frontend
npm install
npm start
```

L'application démarre normalement sur `http://localhost:3000`. Son client API
est actuellement configuré pour joindre `http://localhost:8000/api/`.

## Structure du projet

```text
mon_agenda/
├── AGENTS.md
├── README.md
├── docs/
│   ├── llm-contract.md
│   └── llm-cache-quota-logging.md
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── backend/                 # Paramètres Django et routes racine
│   ├── agenda/                  # Modèles métier et migrations
│   └── api/                     # API REST, auth, LLM, cache, signaux et tests
└── frontend/
    ├── package.json
    └── src/
        ├── components/          # Tâches, catégories, dashboard, recommandations
        ├── context/             # Authentification React
        ├── pages/               # Accueil, connexion, inscription, récupération, paramètres
        └── services/api.js       # Client Axios
```

## API disponible

Toutes les routes API sont préfixées par `/api/`.

| Méthode | Route | Description |
| --- | --- | --- |
| POST | `/api/auth/login/` | Connexion par `identifier` (e-mail ou username) et création d'un token ; cinq tentatives anonymes par quinze minutes |
| POST | `/api/auth/register/` | Inscription avec `email`, `password` et `password_confirmation`, connexion automatique et username interne généré ; cinq tentatives anonymes par heure et par IP |
| POST | `/api/auth/mot-de-passe-oublie/` | Demande de lien de réinitialisation ; réponse identique pour tout e-mail, quota de cinq par IP et trois par e-mail normalisé et haché |
| POST | `/api/auth/reinitialiser-mot-de-passe/` | Réinitialisation avec `uid`, `token`, `password` et `password_confirmation` ; token Django et quota de cinq tentatives par IP |
| POST | `/api/auth/logout/` | Suppression du token courant |
| GET | `/api/auth/user/` | Utilisateur authentifié courant |
| GET, POST | `/api/taches/` | Liste ou création des tâches de l'utilisateur |
| GET, PUT, PATCH, DELETE | `/api/taches/{id}/` | Consultation, modification ou suppression d'une tâche |
| GET | `/api/taches/aujourd_hui/` | Tâches dont l'échéance est aujourd'hui |
| GET | `/api/taches/cette_semaine/` | Tâches de la semaine ISO courante, lundi a dimanche |
| GET | `/api/taches/statistiques/` | Totaux, taux de complétion et priorités 1 a 4 |
| GET | `/api/taches/meilleur_moment/` | Recommandation basée sur les statistiques d'utilisation disponibles |
| GET | `/api/taches/recommandation_ia/` | Recommandation LLM avec cache, quota et repli local |
| GET, POST | `/api/categories/` | Liste ou création des catégories de l'utilisateur |
| GET, PUT, PATCH, DELETE | `/api/categories/{id}/` | Consultation, modification ou suppression d'une catégorie |
| GET, POST | `/api/preferences/` | Liste ou création des préférences de l'utilisateur |
| GET, PUT, PATCH, DELETE | `/api/preferences/{id}/` | Consultation, modification ou suppression de préférences |

L'administration Django est accessible sur `/admin/`.

La réponse de recommandation, qu'elle provienne du LLM ou du repli, respecte :

```json
{
  "heures_recommandees": [9, 14],
  "message": "Une recommandation concise."
}
```

Le format détaillé du prompt et du JSON est documenté dans
[docs/llm-contract.md](docs/llm-contract.md).

## Tests

### Backend

```bash
cd backend
python manage.py test
```

### Frontend

```bash
cd frontend
npm test -- --watchAll=false
```

## État d'avancement

Consulter [AGENTS.md](AGENTS.md) pour les fonctionnalités validées, les limites
connues et l'état détaillé du pipeline de recommandations LLM.
