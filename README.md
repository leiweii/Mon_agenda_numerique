# 📅 Mon Agenda Numérique

**Mon Agenda Numérique** est une application web moderne de gestion de tâches et d'agenda personnel, développée avec Django et React. L'application offre une expérience utilisateur intuitive et personnalisable pour organiser efficacement son quotidien.
---

## 🚀 Fonctionnalités

- ✅ Gestion complète des tâches (CRUD)
- 🎨 Personnalisation avec couleurs et emojis
- 📊 Dashboard avec statistiques et graphiques
- 🤖 Recommandations IA basées sur vos habitudes
- 📁 Organisation par catégories
- 🎯 Système de priorités (4 niveaux)
- 📱 Interface responsive (mobile, tablette, desktop)
- 🔔 Notifications configurables
- 🌓 Mode clair/sombre

---

## 🛠️ Technologies Utilisées

### Backend
- Python
- Django
- Django REST Framework
- PostgreSQL
- Token Authentication

### Frontend
- React 18
- Material-UI (MUI)
- React Router v6
- Axios
- Recharts
- date-fns

---

## 🔧 Installation

### 1. Cloner le projet
```bash
git clone https://github.com/leiweii/Mon_agenda_numerique.git
cd mon-agenda-numerique
```

### 2. Configuration de la Base de Données

Créez la base de données PostgreSQL :
```sql
CREATE DATABASE agenda_numerique;
CREATE USER agenda_user WITH PASSWORD 'mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE agenda_numerique TO agenda_user;
```

### 3. Installation du Backend
```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# Installer les dépendances
pip install django djangorestframework django-cors-headers psycopg2-binary python-decouple pillow

# Créer le fichier .env à la racine
echo "DATABASE_NAME=agenda_numerique" > .env
echo "DATABASE_USER=agenda_user" >> .env
echo "DATABASE_PASSWORD=votre_mot_de_passe" >> .env
echo "DATABASE_HOST=localhost" >> .env
echo "DATABASE_PORT=5432" >> .env
echo "SECRET_KEY=votre-cle-secrete-django" >> .env

# Appliquer les migrations
python manage.py makemigrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

Le backend sera accessible sur `http://localhost:8000`

### 4. Installation du Frontend
```bash
# Aller dans le dossier frontend
cd frontend

# Installer les dépendances
npm install

# Lancer l'application React
npm start
```

Le frontend sera accessible sur `http://localhost:3000`

---

## 📁 Structure du Projet
```
mon-agenda-numerique/
├── backend/
│   ├── agenda/                 # App principale
│   │   ├── models.py          # Modèles de données
│   │   ├── admin.py           # Interface admin
│   │   └── migrations/        # Migrations DB
│   ├── api/                   # API REST
│   │   ├── views.py           # Vues API
│   │   ├── serializers.py     # Sérialiseurs
│   │   ├── urls.py            # Routes API
│   │   └── authentication.py  # Auth
│   ├── backend/               # Configuration Django
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── manage.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/        # Composants React
│   │   │   ├── Layout/
│   │   │   ├── Taches/
│   │   │   ├── Categories/
│   │   │   └── Statistiques/
│   │   ├── pages/             # Pages
│   │   │   ├── Login.jsx
│   │   │   ├── Home.jsx
│   │   │   └── Parametres.jsx
│   │   ├── services/          # Services API
│   │   │   └── api.js
│   │   ├── context/           # Context React
│   │   │   └── AuthContext.jsx
│   │   ├── App.jsx            # App principale
│   │   └── index.js
│   ├── package.json
│   └── README.md
├── README.md
├── PRESENTATION.md
└── .gitignore
```

---

## 🎯 Utilisation

### 1. Connexion

- Ouvrez `http://localhost:3000`
- Connectez-vous avec votre superutilisateur Django

### 2. Créer une Tâche

1. Cliquez sur "Nouvelle tâche"
2. Remplissez le formulaire :
   - Titre
   - Description (optionnel)
   - Date d'échéance
   - Priorité (1-4)
   - Catégorie (optionnel)
3. Personnalisez avec un emoji et une couleur
4. Cliquez sur "Créer"

### 3. Gérer les Catégories

1. Allez dans "Catégories"
2. Créez vos catégories personnalisées
3. Attribuez-les à vos tâches

### 4. Consulter les Statistiques

1. Visitez le "Tableau de bord"
2. Visualisez :
   - Total de tâches
   - Taux de complétion
   - Graphiques de priorités
   - Recommandations IA

### 5. Configurer les Préférences

1. Allez dans "Paramètres"
2. Définissez :
   - Heures productives
   - Thème (clair/sombre)
   - Notifications

---

## 🔌 API Endpoints

### Authentification
```
POST   /api/auth/login/          # Connexion
POST   /api/auth/logout/         # Déconnexion
GET    /api/auth/user/           # Utilisateur actuel
```

### Tâches
```
GET    /api/taches/              # Liste toutes les tâches
POST   /api/taches/              # Créer une tâche
GET    /api/taches/{id}/         # Détails d'une tâche
PUT    /api/taches/{id}/         # Modifier une tâche
DELETE /api/taches/{id}/         # Supprimer une tâche
GET    /api/taches/aujourd_hui/  # Tâches du jour
GET    /api/taches/cette_semaine/ # Tâches de la semaine
GET    /api/taches/statistiques/  # Statistiques
GET    /api/taches/meilleur_moment/ # Recommandations
```

### Catégories
```
GET    /api/categories/          # Liste des catégories
POST   /api/categories/          # Créer une catégorie
PUT    /api/categories/{id}/     # Modifier une catégorie
DELETE /api/categories/{id}/     # Supprimer une catégorie
```

### Préférences
```
GET    /api/preferences/         # Préférences utilisateur
PUT    /api/preferences/{id}/    # Modifier préférences
```

---

## 🧪 Tests

### Backend
```bash
python manage.py test
```

### Frontend
```bash
cd frontend
npm test
```
