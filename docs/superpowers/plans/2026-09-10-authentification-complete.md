# Authentification complète Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter l'authentification par e-mail ou username, l'inscription par e-mail et le reset de mot de passe sécurisé.

**Architecture:** Un backend Django résout l'e-mail ou le username ; les vues DRF appliquent tokens, quotas et contrats HTTP. React Router 7 expose les formulaires publics et tous les formulaires lisent le même extracteur d'erreur API.

**Tech Stack:** Django 6, DRF, cache Django, React 19, React Router 7, MUI 7, Jest.

**Spec:** `docs/superpowers/specs/2026-09-10-authentification-complete-design.md`

## Global Constraints

- Aucun mot de passe ou secret n'est stocké en clair.
- Login : toujours `401` et `Identifiants invalides` en cas de credentials erronés.
- Reset demandé : toujours `200` et le même message, compte existant ou absent.
- Quotas : inscription `5/hour`, login `5/15min`, reset IP `5/hour`, reset e-mail `3/hour`, réinitialisation `5/hour`.
- Chaque comportement commence par un test rouge observé.

### Task 1: Backend d'identifiant et inscription e-mail

**Files:** create `backend/api/auth_backends.py`; modify `backend/api/authentication.py`, `backend/api/urls.py`, `backend/backend/settings.py`, `backend/api/tests.py`.

**Produces:** `EmailOuUsernameBackend.authenticate(...)`; inscription avec `email`, `password`, `password_confirmation`.

- [ ] Écrire les tests rouges : inscription sans username, confirmation refusée, hash `pbkdf2_`, collision `jean.dupont@gmail.com` / `jean-dupont@yahoo.fr`, login username existant et e-mail nouveau.

```python
response = self.client.post('/api/auth/register/', {
    'email': 'jean.dupont@gmail.com',
    'password': 'Une phrase de passe robuste 2026!',
    'password_confirmation': 'Une phrase de passe robuste 2026!',
}, format='json')
user = User.objects.get(email='jean.dupont@gmail.com')
self.assertEqual(response.status_code, 201)
self.assertTrue(user.password.startswith('pbkdf2_'))
```

- [ ] Vérifier l'échec : `cd backend; ..\venv\Scripts\python.exe manage.py test api.tests.AuthenticationEndpointsTests --keepdb`.
- [ ] Implémenter `EmailOuUsernameBackend` avec recherche `email__iexact` si l'identifiant contient `@`, sinon `username__iexact`; refuser compte inactif et utiliser `check_password`.
- [ ] Générer un username interne `slugify(local_part)` avec suffixes `-2`, `-3` sous 150 caractères, puis `validate_password` et `set_password`.
- [ ] Vérifier le vert avec la commande ciblée et committer : `git add backend/api && git commit -m "feat: authentifie par e-mail ou nom d'utilisateur"`.

### Task 2: Rate limiting inscription et connexion

**Files:** modify `backend/api/authentication.py`, `backend/backend/settings.py`, `backend/api/tests.py`.

**Produces:** `LoginRateThrottle` appliqué à `POST /api/auth/login/`.

- [ ] Écrire les tests rouges : trois échecs de login gardent `401`, le sixième garde `429`, et compte absent/mauvais mot de passe renvoient le même JSON.

```python
for _ in range(3):
    self.assertEqual(self.client.post('/api/auth/login/', bad_payload, format='json').status_code, 401)
for _ in range(2):
    self.client.post('/api/auth/login/', bad_payload, format='json')
self.assertEqual(self.client.post('/api/auth/login/', bad_payload, format='json').status_code, 429)
```

- [ ] Vérifier l'échec avec les tests d'authentification.
- [ ] Implémenter `class LoginRateThrottle(AnonRateThrottle): scope = 'login'`, ajouter `login: '5/15min'`, vider le cache dans `setUp`, puis vérifier le vert.
- [ ] Commit : `git add backend/api/authentication.py backend/backend/settings.py backend/api/tests.py && git commit -m "feat: limite les tentatives de connexion"`.

### Task 3: Demande et réinitialisation de mot de passe

**Files:** modify `backend/api/authentication.py`, `backend/api/urls.py`, `backend/backend/settings.py`, `backend/api/tests.py`.

**Produces:** `POST /api/auth/mot-de-passe-oublie/` et `POST /api/auth/reinitialiser-mot-de-passe/`.

- [ ] Écrire les tests rouges : réponse générique pour e-mail connu/inconnu, message en console pour un compte existant, token valide, token invalide, token expiré, mot de passe changé et token invalidé.

```python
response = self.client.post('/api/auth/mot-de-passe-oublie/', {'email': 'alice@example.com'}, format='json')
self.assertEqual(response.data, {'message': 'Si ce compte existe, un e-mail a été envoyé.'})
self.assertEqual(len(mail.outbox), 1)
```

- [ ] Vérifier l'échec car les routes n'existent pas.
- [ ] Utiliser `urlsafe_base64_encode`, `default_token_generator`, `send_mail` et `FRONTEND_URL`; configurer le backend console par défaut et les variables SMTP.
- [ ] Ajouter throttles IP, e-mail haché SHA-256 et réinitialisation, puis vérifier le vert.
- [ ] Commit : `git add backend/api && git commit -m "feat: ajoute la réinitialisation de mot de passe"`.

### Task 4: Utilitaire d'erreurs et formulaires React Router 7

**Files:** create `frontend/src/services/errors.js`, `frontend/src/services/errors.test.js`, `frontend/src/pages/MotDePasseOublie.jsx`, `frontend/src/pages/MotDePasseOublie.test.jsx`, `frontend/src/pages/ReinitialiserMotDePasse.jsx`, `frontend/src/pages/ReinitialiserMotDePasse.test.jsx`; modify `Inscription`, `Login`, `AuthContext`, `api.js`, `App.js` et leurs tests.

**Produces:** `extraireMessageErreur`, pages publiques oubli/reset et routes `/mot-de-passe-oublie`, `/reinitialiser-mot-de-passe/:uid/:token`.

- [ ] Écrire les tests rouges pour `error`, `detail`, `non_field_errors`, fallback, `429` d'inscription/login, confirmation frontend, reset invalide et liens Login.

```javascript
expect(extraireMessageErreur({ response: { data: { error: 'Erreur' } } }, 'Fallback')).toBe('Erreur');
expect(extraireMessageErreur({ response: { data: { detail: 'Trop de tentatives' } } }, 'Fallback')).toBe('Trop de tentatives');
expect(extraireMessageErreur({ response: { data: { non_field_errors: ['Invalide'] } } }, 'Fallback')).toBe('Invalide');
```

- [ ] Vérifier l'échec : `cd frontend; npm test -- --watchAll=false --runInBand errors.test.js Inscription.test.jsx Login.test.jsx MotDePasseOublie.test.jsx ReinitialiserMotDePasse.test.jsx`.
- [ ] Implémenter l'extracteur dans l'ordre `error`, `detail`, `non_field_errors`, fallback; l'appliquer aux quatre formulaires; envoyer `identifier` au login et ajouter les routes avec `useParams`.
- [ ] Vérifier le vert puis committer : `git add frontend/src && git commit -m "feat: ajoute les formulaires de récupération de compte"`.

### Task 5: Documentation et vérification intégrée

**Files:** modify `AGENTS.md`, `README.md`.

- [ ] Documenter endpoints, variables `FRONTEND_URL`/SMTP et cocher l'état Auth après les tests.
- [ ] Exécuter `cd backend; ..\venv\Scripts\python.exe manage.py test --keepdb` et `cd frontend; npm test -- --watchAll=false --runInBand`.
- [ ] Démarrer les serveurs, créer les deux comptes de collision, se connecter dans le navigateur par username existant puis e-mail nouveau, faire trois puis six échecs de login, et parcourir le lien de reset de l'e-mail console.
- [ ] Vérifier en shell : `User.objects.get(email='jean.dupont@gmail.com').password.startswith('pbkdf2_')` et `check_password(...)`.
- [ ] Relire `git diff --check`, puis committer : `git add AGENTS.md README.md && git commit -m "docs: documente l'authentification complète"`.

## Self-review

- Couverture : identifiant, inscription, hash, collision, quotas, reset, SMTP, routes React Router 7, extracteur d'erreur, tests et navigateur sont couverts.
- Placeholders : aucun `TODO` ni `TBD`.
- Cohérence : les routes, scopes et interfaces reprennent la spécification validée.
