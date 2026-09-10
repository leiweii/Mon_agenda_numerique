# 📅 Mon Agenda Numérique

**Mon Agenda Numérique** est une application web de gestion de tâches et d'agenda
personnel, développée avec Django et React.

> 🚧 **Projet en cours de finalisation.** Certaines fonctionnalités ci-dessous sont
> encore incomplètes ou en développement. Voir [`AGENTS.md`](./AGENTS.md) pour l'état
> d'avancement détaillé et la feuille de route de développement.

---

## 🚀 Fonctionnalités (cible)

- ✅ Gestion complète des tâches (CRUD)
- 🎨 Personnalisation avec couleurs et emojis
- 📊 Dashboard avec statistiques et graphiques
- 🤖 Recommandations IA basées sur vos habitudes (pipeline LLM en cours d'intégration)
- 📁 Organisation par catégories
- 🎯 Système de priorités (4 niveaux)
- 📱 Interface responsive (mobile, tablette, desktop)
- 🔔 Notifications configurables
- 🌓 Mode clair/sombre

*Pour savoir précisément ce qui est déjà fonctionnel, voir la section "État
d'avancement" dans [`AGENTS.md`](./AGENTS.md).*

---

## 🛠️ Technologies Utilisées

### Backend
- Python, Django, Django REST Framework
- PostgreSQL
- Token Authentication

### Frontend
- React 18, Material-UI (MUI)
- React Router v6, Axios, Recharts, date-fns

---

## 🔧 Installation

### 1. Cloner le projet
```bash
git clone https://github.com/leiweii/Mon_agenda_numerique.git
cd mon-agenda-numerique
```

### 2. Configuration de la base de données
```sql
CREATE DATABASE agenda_numerique;
CREATE USER agenda_user WITH PASSWORD 'mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE agenda_numerique TO agenda_user;
```

### 3. Backend
```bash
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate

pip install django djangorestframework django-cors-headers psycopg2-binary python-decouple pillow anthropic

echo "DATABASE_NAME=agenda_numerique" > .env
echo "DATABASE_USER=agenda_user" >> .env
echo "DATABASE_PASSWORD=votre_mot_de_passe" >> .env
echo "DATABASE_HOST=localhost" >> .env
echo "DATABASE_PORT=5432" >> .env
echo "SECRET_KEY=votre-cle-secrete-django" >> .env
echo "LLM_API_KEY=votre-cle-api-llm" >> .env

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Backend accessible sur `http://localhost:8000`

### 4. Frontend
```bash
cd frontend
npm install
npm start
```
Frontend accessible sur `http://localhost:3000`

---

## 📁 Structure du Projet
```
mon-agenda-numerique/
├── backend/
│   ├── agenda/
│   │   ├── models.py
│   │   ├── admin.py
│   │   └── migrations/
│   ├── api/
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── authentication.py
│   │   └── llm_service.py      # pipeline LLM (voir AGENTS.md)
│   ├── backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   ├── Taches/
│   │   │   ├── Categories/
│   │   │   ├── Statistiques/
│   │   │   └── RecommandationsIA.jsx
│   │   ├── pages/
│   │   ├── services/
│   │   ├── context/
│   │   └── App.jsx
│   └── package.json
├── README.md
└── AGENTS.md                    # guide de travail pour l'agent Codex
```

---

## 🎯 Utilisation

1. **Connexion** — `http://localhost:3000`, se connecter avec le superutilisateur
2. **Créer une tâche** — titre, description, échéance, priorité, catégorie, emoji, couleur
3. **Gérer les catégories** — créer et attribuer aux tâches
4. **Tableau de bord** — total de tâches, taux de complétion, graphiques, recommandations
5. **Paramètres** — heures productives, thème, notifications

---

## 🔌 API Endpoints

### Authentification
```
POST   /api/auth/login/
POST   /api/auth/logout/
GET    /api/auth/user/
```

### Tâches
```
GET    /api/taches/
POST   /api/taches/
GET    /api/taches/{id}/
PUT    /api/taches/{id}/
DELETE /api/taches/{id}/
GET    /api/taches/aujourd_hui/
GET    /api/taches/cette_semaine/
GET    /api/taches/statistiques/
GET    /api/taches/meilleur_moment/
```

### Catégories
```
GET    /api/categories/
POST   /api/categories/
PUT    /api/categories/{id}/
DELETE /api/categories/{id}/
```

### Préférences
```
GET    /api/preferences/
PUT    /api/preferences/{id}/
```

---

## 🧪 Tests

```bash
python manage.py test        # backend
cd frontend && npm test      # frontend
```

---

## 🤝 Pour contribuer / développer avec un agent IA (Codex)

Ce projet utilise un fichier [`AGENTS.md`](./AGENTS.md) qui décrit :
- les règles de travail (une tâche = un commit, tests obligatoires, etc.)
- l'état d'avancement réel de chaque fonctionnalité
- la feuille de route du pipeline de recommandations LLM

**Toujours consulter et tenir à jour `AGENTS.md` avant/après chaque tâche.**
