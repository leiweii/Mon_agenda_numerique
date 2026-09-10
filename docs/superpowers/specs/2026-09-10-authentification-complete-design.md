# Conception - authentification complete

## Objectif

Completer l'authentification de Mon Agenda Numerique sans remplacer le modele
utilisateur Django existant. Les comptes existants continuent a se connecter avec
leur nom d'utilisateur et les nouveaux comptes utilisent leur e-mail dans le
meme champ de connexion.

## Decisions de contrat

- Le formulaire de connexion envoie `identifier` et `password`. L'API accepte
  egalement `username` temporairement pour ne pas casser les clients actuels.
- `EmailOuUsernameBackend` choisit la recherche par e-mail si l'identifiant
  contient `@`, sinon par username. Il refuse les comptes inactifs et utilise
  `check_password`; aucun mot de passe n'est compare en clair.
- L'inscription accepte `email`, `password` et `password_confirmation`.
  L'e-mail est normalise en minuscules et controle avant creation.
- Le username est interne pour les nouveaux comptes. Il est derive de la partie
  locale de l'e-mail avec `slugify`, borne a 150 caracteres et suffixe avec
  `-2`, `-3`, etc. jusqu'a trouver une valeur libre. Si le slug est vide, le
  prefixe `utilisateur` est utilise.
- Le rejet de connexion est toujours `401` avec `Identifiants invalides`.
  Il ne distingue pas compte absent, e-mail inconnu ou mot de passe incorrect.
- L'inscription signale clairement qu'une adresse e-mail est deja utilisee,
  conformement au contrat produit. La confirmation de mot de passe est verifiee
  cote client et cote serveur.

## Backend

### Authentification et inscription

`api/authentication.py` recevra le backend `EmailOuUsernameBackend`, les
helpers de reponse de session et de generation de username, et les vues
fonctionnelles suivantes :

- `POST /api/auth/login/`
- `POST /api/auth/register/`
- `POST /api/auth/mot-de-passe-oublie/`
- `POST /api/auth/reinitialiser-mot-de-passe/`
- `POST /api/auth/logout/`
- `GET /api/auth/user/`

Le backend sera declare dans `AUTHENTICATION_BACKENDS`, en conservant aussi le
backend Django standard. L'inscription appelle `validate_password` avec le
nouvel utilisateur avant `set_password`; le champ `password` stocke ainsi le
hash configure par Django, jamais la valeur soumise.

L'unicite d'e-mail est appliquee par l'API avec une recherche insensible a la
casse. Le modele `auth.User` ne rend pas nativement l'e-mail unique, donc ce
changement ne pretend pas apporter une contrainte transactionnelle en base :
une migration vers un modele utilisateur personnalise serait un projet distinct
et incompatible avec le perimetre actuel.

### Mot de passe oublie

La demande de reset normalise l'e-mail, repond toujours `200` avec :

```json
{"message": "Si ce compte existe, un e-mail a ete envoye."}
```

Si l'utilisateur existe et est actif, elle construit l'URL frontend
`{FRONTEND_URL}/reinitialiser-mot-de-passe/{uid}/{token}` avec
`urlsafe_base64_encode` et `PasswordResetTokenGenerator`, puis appelle
`send_mail`. Le token est verifie avant toute ecriture par la vue de
reinitialisation. Apres `set_password`, Django invalide automatiquement le
token utilise.

`backend/settings.py` utilisera le backend console par defaut en developpement.
Les deployments SMTP pourront definir `EMAIL_BACKEND`, `EMAIL_HOST`,
`EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` et `FRONTEND_URL` dans l'environnement.
Aucun secret SMTP ne sera ajoute au frontend ou au depot.

### Rate limiting

Des throttles DRF bases sur le cache seront scopes par action :

- inscription : 5 tentatives par heure et par IP ;
- connexion : 5 tentatives par 15 minutes et par IP ;
- demande de reset : 5 demandes par heure et par IP, plus 3 par heure pour le
  hash SHA-256 de l'e-mail normalise ;
- reinitialisation : 5 tentatives par heure et par IP.

Les erreurs de throttle gardent le statut `429`; le frontend utilise `detail`
pour expliquer l'attente sans exposer l'existence d'un compte.

## Frontend React Router 7

React Router est en version 7.13 et les composants existants utilisent
`Routes` et `Route`. Les routes publiques suivantes seront ajoutees avec cette
API :

- `/inscription`
- `/mot-de-passe-oublie`
- `/reinitialiser-mot-de-passe/:uid/:token`

`Login.jsx` devient un formulaire `E-mail ou nom d'utilisateur` plus mot de
passe, avec les liens vers inscription et oubli. `Inscription.jsx` n'affiche
plus de username. Les pages oubli et reset affichent les erreurs explicites
(token invalide, mot de passe invalide) et conservent le message de demande de
reset generique. `AuthContext` conserve l'etablissement de session unique apres
connexion ou inscription.

## Tests et verification

Tests automatises backend :

- inscription par e-mail, confirmation invalide, e-mail duplique et validateurs
  Django ;
- usernames generes sans collision avec `jean.dupont@gmail.com` puis
  `jean-dupont@yahoo.fr` ;
- connexion d'un compte existant par username et d'un nouveau compte par e-mail ;
- erreur de connexion identique pour compte absent et mot de passe invalide ;
- quotas connexion apres 5 echecs en 15 minutes, sans blocage apres 2 ou 3 ;
- demande de reset generique pour e-mail existant ou absent, email envoye dans
  le backend console, token valide, invalide et expire ;
- reinitialisation qui modifie le hash du mot de passe et invalide le token.

Tests frontend : rendu, validations de confirmation, succes, erreur backend et
`429` pour connexion, inscription, oubli et reset ; routes et liens Login.

Verification manuelle obligatoire avec les serveurs Django et React demarres :

1. Creer un compte et inspecter `User.password` depuis `manage.py shell` : la
   valeur doit etre un hash Django, tel que `pbkdf2_sha256$...`, jamais le mot
   de passe.
2. Se connecter dans le navigateur avec un utilisateur existant par username,
   puis avec un compte nouvellement cree par e-mail.
3. Verifier les deux e-mails de collision de slug et le suffixe du second
   username genere.
4. Verifier dans le navigateur que cinq echecs de connexion declenchent `429`,
   alors que deux ou trois echecs consecutifs restent traites normalement.
5. Demander un reset, recuperer le lien du backend console, reinitialiser le
   mot de passe et se reconnecter avec la nouvelle valeur.

## Hors perimetre

- Migration vers un modele utilisateur personnalise avec contrainte SQL unique
  sur e-mail.
- Envoi d'e-mail reel sans configuration SMTP de l'environnement.
- Verification d'adresse e-mail et authentification multifacteur.
