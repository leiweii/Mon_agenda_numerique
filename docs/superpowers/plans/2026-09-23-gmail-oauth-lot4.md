# Gmail OAuth lot 4 - plan d'implementation

> Execution locale par lots testes. Le depot contient les lots email 1-3 non commites ; ne pas creer de worktree ni commiter une migration dependant de `0007` avant regularisation.

**Objectif :** connecter un compte Gmail personnel via OAuth 2.0, conserver seulement le refresh token chiffre et signaler clairement une reconnexion necessaire, sans envoyer d'email.

**Architecture :** deux nouveaux modeles (`ConnexionGmail`, `TentativeOAuthGmail`) et un service OAuth cote Django. React n'obtient qu'une URL d'autorisation et un statut non sensible. Le callback Google est lie a l'utilisateur par un `state` aleatoire, expire apres dix minutes et consomme une seule fois ; PKCE S256 protege l'echange de code.

**Spec :** `docs/superpowers/specs/2026-09-22-candidatures-email-spontanee.md`, notamment sections 9, 18, 19, 22 et 23.

## Contraintes

- Variables confirmees : `GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET`, `GMAIL_OAUTH_REDIRECT_URI`, `GMAIL_TOKEN_ENCRYPTION_KEY`.
- Scope Gmail minimal : `https://www.googleapis.com/auth/gmail.send` ; acces hors ligne.
- Aucun secret, token ou code OAuth dans le frontend, les logs ou Git.
- Aucun appel `users.messages.send` dans ce lot.
- Tous les echanges Google sont mocks dans les tests ; aucune connexion reseau reelle.
- Les modifications existantes du depot restent intactes.

## Tache 1 - Modeles et chiffrement

Fichiers : `backend/api/models.py`, migration `api.0008`, `backend/api/test_gmail_oauth.py`, `backend/requirements.txt`, `backend/backend/settings.py`, nouveau `backend/api/gmail_oauth_service.py`.

- [x] Ecrire les tests d'unicite par utilisateur, expiration de tentative a dix minutes, stockage chiffre du refresh token et absence de repli sur une cle non configuree.
- [x] Observer l'echec de ces tests, puis ajouter les modeles et le chiffrement Fernet.
- [x] Generer la migration et verifier qu'aucun autre changement de schema n'apparait.

## Tache 2 - Demarrage et retour OAuth

Fichiers : `backend/api/gmail_oauth_service.py`, nouveau `backend/api/gmail_views.py`, `backend/api/urls.py`, `backend/api/test_gmail_oauth.py`.

- [x] Tester une URL Google avec `state`, PKCE S256, scope `gmail.send`, `access_type=offline`, et aucune divulgation de secret dans la reponse.
- [x] Tester le callback : state absent, expire ou reutilise rejete sans echange ; echange valide cree une connexion utilisateur avec refresh token chiffre ; absence de refresh token donne une erreur neutre.
- [x] Observer les echecs, implementer les quatre endpoints approuves et relancer les tests cibles.

## Tache 3 - Statut, renouvellement et revocation

Fichiers : `backend/api/gmail_oauth_service.py`, `backend/api/gmail_views.py`, `backend/api/test_gmail_oauth.py`.

- [x] Tester l'etat non connecte, le renouvellement valide, la revocation `invalid_grant` et une erreur reseau temporaire distincte.
- [x] Observer les echecs puis implementer le statut et la verification sans exposer de credential.

## Tache 4 - Interface et contrat frontend

Fichiers : nouveau `frontend/src/components/Candidatures/GmailConnectionCard.jsx` et son test, `frontend/src/pages/Parametres.jsx`, `frontend/src/services/api.js`, tests de `Parametres`.

- [x] Tester le bouton Connecter, la navigation vers l'URL renvoyee, l'etat connecte, le message de reconnexion et l'erreur temporaire.
- [x] Observer les echecs puis integrer la carte dans Parametres avec MUI 7 `Grid size`.

## Tache 5 - Verification et documentation

Fichiers : `AGENTS.md` section 5 uniquement pour l'etat du lot.

- [x] Executer les tests backend complets (193), `CI=true; npm test -- --watchAll=false` (87), le controle des migrations et le build frontend.
- [x] Mettre a jour AGENTS.md avec les resultats reellement observes, verifier `git diff --check` et relire le diff.
