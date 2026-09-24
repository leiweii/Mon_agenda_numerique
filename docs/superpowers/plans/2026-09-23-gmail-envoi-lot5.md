# Lot 5 - Envoi Gmail individuel : plan d'implementation

> **Pour l'agent d'execution :** lire la specification et ce plan avant tout
> changement. Executer les taches ci-dessous dans l'ordre, en TDD, sans envoyer
> de vrai message pendant les tests. Le lot forme un seul commit applicatif
> coherent apres verification backend et frontend.

**Objectif :** envoyer individuellement un email `ready` depuis le compte
Gmail connecte, uniquement apres une confirmation distincte, avec CV joint,
protection contre les doubles requetes et historique explicite.

**Architecture :** l'API reserve atomiquement l'email en `sending` avant
l'appel reseau. Un service Gmail construit le MIME et appelle
`users.messages.send` avec le scope OAuth `gmail.send` existant. Seule une
reponse Gmail exploitable marque `sent`; les resultats incertains restent
`sending` et exigent une decision manuelle. Les nouvelles tentatives sont des
`EmailCandidature` distincts lies a la tentative precedente.

**Stack :** Django 6 / DRF / PostgreSQL, `google-auth-oauthlib`, Requests,
React 19 / MUI 7 / Jest.

**Specification :** `docs/superpowers/specs/2026-09-22-candidatures-email-spontanee.md`,
sections 7, 9, 11-13, 17-24 et 28-30. Les clarifications utilisateur du
23/09/2026 precisent que le scope `gmail.metadata` est exclu du lot 5 et que
la confirmation manuelle ou une nouvelle tentative doivent etre possibles
apres un resultat incertain.

## Contraintes globales

- Aucun envoi a la preparation (`draft`) ni au passage a `ready`.
- Le seul point d'envoi est un `POST` authentifie avec confirmation explicite.
- Un email `draft`, `cancelled`, `failed`, `sending` ou `sent` n'est jamais
  envoye par ce point d'entree : seul `ready` peut passer a `sending`.
- Une requete repetee pour le meme email ne declenche jamais un second appel
  Gmail. `sent` retourne l'etat existant ; `sending` retourne un conflit.
- Le CV montre dans la confirmation est recontrole par empreinte du nom et des
  octets lus : si le CV change avant la reservation, refuser l'envoi et exiger
  une nouvelle confirmation. Les octets lus et valides sont ceux joints.
- Une nouvelle tentative apres `sending` est un nouvel enregistrement `draft`,
  ouvert en previsualisation/edition. Elle doit repasser par `ready` puis une
  nouvelle confirmation distincte avant tout appel Gmail.
- `retry_of` pointe vers la tentative precedente : chaine lineaire. Une
  tentative ne peut avoir qu'un successeur direct. Pas de plafond global en V1.
- Les tokens, le MIME brut, le contenu du CV et les reponses Gmail brutes ne
  figurent ni dans les logs, ni dans `error_message`, ni dans le frontend.
- Conserver `gmail.send` seul. Ne pas ajouter de permission de lecture Gmail.
- L'adresse e-mail du compte applicatif est identique au compte Gmail connecte
  ou a un alias d'envoi autorise (confirmation utilisateur). La valider avant
  reservation et l'utiliser comme champ MIME `From` ; ne pas demander de scope
  supplementaire pour lire le profil Gmail.
- Les tests remplacent completement les appels Google et HTTP.
- Mettre a jour uniquement la section 5 d'`AGENTS.md` apres tests passes.

## Decision sur les erreurs et les delais

L'appel a `POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send`
utilise `timeout=(5, 20)` : 5 secondes pour etablir une connexion, puis
20 secondes d'inactivite en lecture. Ce n'est pas un delai total garanti.
`allow_redirects=False` et aucun retry HTTP automatique.

| Observation apres reservation `sending` | Etat final | Motif |
| --- | --- | --- |
| Validation locale avant reservation (email invalide, CV illisible, Gmail absent) | `ready` inchange | Aucun appel Gmail n'a commence. |
| Erreur apres reservation mais avant la transmission du corps (refresh token invalide, `ConnectTimeout`, echec DNS ou handshake TLS identifie) | `failed` | Aucun corps d'envoi n'a pu atteindre Gmail. |
| Reponse HTTP 4xx explicite, sauf 408 | `failed` | Gmail a rejete la requete ; 401 demande une reconnexion. |
| Reponse 2xx avec `id` Gmail non vide | `sent` | Confirmation exploitable ; sauver l'id et l'historique dans la meme transaction. |
| `ReadTimeout`, coupure apres connexion, erreur reseau ou TLS de phase inconnue, HTTP 408/5xx, 2xx sans `id`, arret du processus apres reservation | `sending` | Gmail a peut-etre envoye ; aucun retry automatique. |

Pour `sending`, afficher : « Resultat incertain : Gmail a peut-etre envoye
ce message. Verifiez le dossier Envoyes (destinataire, objet et date). Aucun
renvoi automatique n'aura lieu. » Deux actions explicites :

Pendant une requete d'envoi encore active, afficher plutot « Envoi en
cours » sans ces deux actions. Elles deviennent disponibles lorsque le
service a enregistre l'issue incertaine, ou apres 5 minutes en `sending`
sans resultat (recuperation d'un processus interrompu). Les endpoints
verifient aussi cette condition ; un rafraichissement de page ne peut pas
contourner l'attente. Ce delai est une protection pragmatique, pas une
preuve que Gmail n'a pas envoye.

Le seuil de 5 minutes est calcule a la lecture en comparant `updated_at`
avec l'heure courante ; le serveur le reverifie lors de chaque action. Aucun
job planifie, Celery ou infrastructure supplementaire n'est necessaire.

1. **J'ai verifie : email envoye** : confirmation manuelle sur le meme
   enregistrement, sans appel Gmail. `sent_at` est la date de confirmation,
   `manual_confirmation_at` permet de ne pas la presenter comme la date exacte
   de livraison ; l'historique indique « confirme manuellement ».
2. **Creer une nouvelle tentative** : avertissement de doublon potentiel,
   puis copie du destinataire, objet et corps dans un nouvel
   `EmailCandidature` `draft` avec `retry_of` pointant vers la tentative
   precedente. L'original reste `sending`. Le nouveau brouillon s'ouvre en
   previsualisation/edition ; il doit etre prepare puis confirme avant l'envoi.
   Ce bouton seul n'appelle jamais Gmail. Si un successeur existe deja,
   l'endpoint renvoie ce meme successeur sans en creer un second.
   Si un brouillon de relance est annule, une tentative suivante peut etre
   creee depuis cet enfant `cancelled` ; la chaine reste lineaire et sans
   plafond global.

Si les deux tentatives sont finalement confirmees comme reussies, les deux
emails restent `sent` et deux `ActionCandidature` distinctes apparaissent
dans la timeline, avec les ids et la provenance (« via Gmail » ou « confirme
manuellement »). L'interface montre leur lien `retry_of` et un avertissement
« Deux envois confirmes pour cette chaine de tentatives ». Ne jamais masquer
le doublon dans l'historique.

Cette politique est une deduction des contrats Google : `messages.send` est
un POST, tandis que `messages.list` ne permet pas `gmail.send` seul.
Sources :

- https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
- https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
- https://requests.readthedocs.io/en/stable/user/advanced/#timeouts
- https://requests.readthedocs.io/en/stable/api/#requests.ConnectTimeout

## Structure des fichiers

| Fichier | Responsabilite |
| --- | --- |
| `backend/api/models.py`, migration `0009` | `retry_of` et `manual_confirmation_at` sur `EmailCandidature` ; un seul successeur direct. |
| `backend/api/gmail_send_service.py` | Refresh OAuth, MIME texte + PDF, appel HTTP Gmail et classification sans fuite sensible. |
| `backend/api/email_send_service.py` | Validations, reservation atomique, transitions de statut et historique. |
| `backend/api/views.py` | Upload/remplacement du CV et routes email scopees par `CandidatureViewSet.get_object()`. |
| `backend/backend/settings.py` | `MEDIA_ROOT` prive sous `backend/media/`. |
| `backend/requirements.txt` | Ajouter `requests==2.34.2` comme dependance directe, version testee dans le venv. |
| `backend/api/test_email_send.py` | Tests de validation, concurrence, succes, erreurs et historique avec Gmail mocke. |
| `frontend/src/pages/Parametres.jsx` et composant CV | Upload/remplacement du CV par defaut. |
| `frontend/src/pages/CandidatureDetail.jsx`, `EmailBrouillonDialog.jsx` | Confirmation distincte, etats d'envoi, reconciliation et historique visible. |
| `frontend/src/services/api.js` | Methodes upload, envoyer, confirmer manuellement, nouvelle tentative. |
| Tests React correspondants | Confirmation, loading, succes, echec, double clic et deux tentatives reussies. |
| `AGENTS.md` section 5 | Etat reel et resultats de verification du lot. |

## Review focus

1. Un email `ready` dont l'adresse a ete corrompue en base est refuse avant
   toute requete Gmail : test de validation au moment de l'envoi.
2. Un CV remplace ou supprime entre preparation et envoi est revalide et lu
   avant la reservation : test fichier manquant/inaccessible.
3. Deux POST concurrents sur le meme email ne peuvent reserver qu'une seule
   transition `ready -> sending` : test de concurrence avec Gmail bloque.
4. Une reponse Gmail 2xx sans `id` ne devient jamais `sent` : test du resultat
   incertain et absence d'action d'historique.
5. Une confirmation manuelle apres une relance deja envoyee conserve deux
   traces d'envoi visibles, sans fusion silencieuse : tests backend et React.

---

### Task 1 : CV par defaut prive et metadonnees de tentative

**Fichiers :** modifier `backend/api/models.py`, `backend/api/views.py`,
`backend/backend/settings.py`, `backend/requirements.txt` ; creer la migration
`backend/api/migrations/0009_emailcandidature_manual_confirmation_retry.py` ;
ajouter les tests dans `backend/api/test_email_send.py`.

**Interfaces :** `PUT /api/candidatures/cv_par_defaut/` recoit `multipart/form-data`
avec `fichier` et renvoie `{filename: "nom.pdf"}`. Le `GET` existant reste
compatible. Aucun endpoint public ne sert le contenu du CV.

- [ ] Ecrire les tests : proprietaire du CV, remplacement du meme enregistrement,
  fichier PDF valide, rejet extension/signature non PDF, rejet > 5 Mio,
  fichier absent, suppression de l'ancien fichier apres remplacement et
  conservation de l'ancien si l'upload echoue. Isoler `MEDIA_ROOT` dans un
  repertoire temporaire par test ; ne jamais ecrire dans `backend/media/`
  pendant la suite.
- [ ] Verifier le rouge avec `..\venv\Scripts\python.exe manage.py test api.test_email_send`.
- [ ] Ajouter `manual_confirmation_at = models.DateTimeField(null=True, blank=True)`
  et `retry_of = models.ForeignKey('self', null=True, blank=True,
  on_delete=models.SET_NULL, related_name='retry_attempts')`, avec contrainte
  d'unicite conditionnelle sur `retry_of` non nul ; generer `0009`.
- [ ] Configurer `MEDIA_ROOT = BASE_DIR / 'media'` (repertoire deja ignore),
  stockage prive non servi par URL. Accepter uniquement un nom `.pdf`, une
  signature `%PDF-` et au plus 5 Mio ; ne jamais faire confiance au seul
  `content_type`. Utiliser le `OneToOneField` existant, pas de second CV V1.
- [ ] Verifier le vert avec la meme commande, puis verifier
  `makemigrations --check --dry-run`.

### Task 2 : service Gmail injectable et sans retry automatique

**Fichiers :** creer `backend/api/gmail_send_service.py` et
`backend/api/test_gmail_send_service.py` ; modifier `backend/requirements.txt`.

**Interfaces :** `envoyer_message_gmail(*, connexion, recipient, subject,
body, cv_bytes, cv_filename) -> gmail_message_id` ou leve une exception
typisee `EnvoiRefuse(code)` / `ResultatIncertain(code)` ; jamais d'exception
contenant un token ou le corps de reponse Gmail dans la sortie publique.

- [ ] Ecrire les tests MIME : `From`, `To`, `Subject`, texte UTF-8, PDF joint sous
  son nom, `raw` base64url ; `messages.send` recoit uniquement un message
  individuel. Mocker `Credentials.refresh` et `requests.post` ; bloquer tout
  socket reel. Decoder `raw` avec `base64.urlsafe_b64decode`, puis
  `email.message_from_bytes` pour inspecter le message et la piece jointe.
- [ ] Verifier le rouge avec `..\venv\Scripts\python.exe manage.py test api.test_gmail_send_service`.
- [ ] Construire un `email.message.EmailMessage`, `set_content(body)` et
  `add_attachment(cv_bytes, maintype='application', subtype='pdf',
  filename=cv_filename)` ; encoder `base64.urlsafe_b64encode(message.as_bytes())`
  dans `raw`.
- [ ] Rafraichir le token avant l'appel d'envoi, puis utiliser
  `requests.post('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
  headers={'Authorization': f'Bearer {access_token}'}, json={'raw': raw},
  timeout=(5, 20), allow_redirects=False)`. Le transport mocke doit etre
  injectable ; aucune relance automatique du POST. Declarer
  `requests==2.34.2` dans `backend/requirements.txt`.
- [ ] Tester les classifications : succes avec id ; `ConnectTimeout`, echec
  DNS, handshake TLS et 4xx (sauf 408) refuses ; `ReadTimeout`,
  `ConnectionError` de phase inconnue, 408, 5xx et 2xx sans id incertains ; refresh invalide
  avant POST demande une reconnexion sans appel Gmail.
- [ ] Verifier le vert avec le meme module de tests.

### Task 3 : envoi atomique, confirmation manuelle et historique

**Fichiers :** creer `backend/api/email_send_service.py` ; modifier
`backend/api/views.py`, `backend/api/serializers.py` si necessaire ; ajouter
les tests dans `backend/api/test_email_send.py`.

**Interfaces :**

| Methode et route | Effet |
| --- | --- |
| `POST /api/candidatures/{id}/emails/{email_id}/envoyer/` avec `{confirmation: true, cv_fingerprint: "..."}` | Seul `ready` part vers Gmail et l'empreinte du CV confirme doit correspondre aux octets joints. `sent` retourne l'etat existant sans renvoi ; `sending` retourne 409. |
| `POST /api/candidatures/{id}/emails/{email_id}/confirmer_manuellement/` avec `{confirmation: true}` | Seul `sending` devient `sent` sans Gmail. |
| `POST /api/candidatures/{id}/emails/{email_id}/nouvelle_tentative/` avec `{confirmation: true}` | Seul `sending`, `failed` ou un enfant `cancelled` cree une copie `draft` liee a la tentative precedente, sans Gmail. Repetition : meme successeur. |

Reponses d'envoi : `200` avec l'email `sent` au succes (ou a une repetition
apres succes) ; `202` avec l'email encore `sending` pour un resultat
incertain ; `502` avec l'email `failed` pour un refus Gmail certain ; `400`
pour confirmation absente, email invalide ou CV inaccessible ; `409` si le CV
ne correspond plus a celui confirme ; `404` pour
parent/email hors scope ; `409` pour `draft`, `cancelled`, `failed`, `sending`
ou Gmail non connecte. Un token revoque renvoie un message de reconnexion.

- [ ] Ecrire d'abord les tests DRF : authentification, scoping par parent et
  email, id inexistant, email invalide, `draft` non pret, CV absent/illisible,
  Gmail absent/revoque, appel Gmail unique au succes, `sent_at` et
  `gmail_message_id`, erreur certaine `failed`, issue incertaine `sending`,
  double POST sequentiel et concurrent, pas d'historique sur echec, un seul
  historique sur succes, confirmation manuelle, duplication apres `sending`,
  deux succes finaux dans une chaine et refus a l'autre utilisateur. Tester
  aussi le refus des actions manuelles pendant les 5 premieres minutes
  d'un `sending` sans erreur, puis leur ouverture apres ce delai.
  Les tests de double clic affirment `post_mock.call_count == 1` ; ceux de
  `sending` affirment `post_mock.assert_not_called()` et absence d'action
  `envoyee` tant que l'utilisateur n'a pas confirme manuellement.
- [ ] Verifier le rouge avec `..\venv\Scripts\python.exe manage.py test api.test_email_send`.
- [ ] Charger l'email via la candidature deja scopee par `get_object()`.
  Valider a nouveau l'adresse (`validate_email`), le sujet, le corps, le CV
  ouvert en lecture et le compte Gmail ; preparer les octets du CV avant
  toute reservation. Aucun contenu du POST ne peut modifier le brouillon.
  Ajouter `retry_of` et `manual_confirmation_at` aux champs en lecture seule
  d'`EmailCandidatureSerializer`.
- [ ] Dans `transaction.atomic()` avec `select_for_update()`, reserver
  `ready -> sending`, enregistrer et sortir de la transaction **avant** le
  reseau. Une requete concurrente constate `sending` et n'appelle pas Gmail.
- [ ] Apres reponse exploitable, mettre `sent`, `sent_at`,
  `gmail_message_id` et creer une seule `ActionCandidature` de type
  `envoyee` dans la meme transaction. Sur `EnvoiRefuse`, mettre `failed` et
  une erreur courte non sensible ; sur `ResultatIncertain`, conserver
  `sending` et une raison courte non sensible. Ne jamais marquer `sent` par
  simple absence d'exception.
- [ ] La confirmation manuelle cree l'action avec le libelle « confirme
  manuellement apres resultat incertain » et renseigne
  `manual_confirmation_at`. La nouvelle tentative `draft` copie les champs
  redactionnels, pas `gmail_message_id` ni `sent_at`, et laisse l'original
  intact.
- [ ] Verifier le vert avec le meme module et les tests email existants de
  la section 23 (template, fallback, aucune requete Gmail a la preparation).

### Task 4 : upload/remplacement du CV dans Parametres

**Fichiers :** creer
`frontend/src/components/Candidatures/DefaultCvCard.jsx` et son test ;
modifier `frontend/src/pages/Parametres.jsx`, ses tests et
`frontend/src/services/api.js`.

**Interfaces :** `candidaturesAPI.replaceDefaultCv(file)` emet un `PUT`
multipart ; `getDefaultCv()` retourne le nom et une empreinte du fichier prive
pour la confirmation d'envoi. La carte affiche le
fichier actuel, un controle de selection PDF, « Ajouter » ou « Remplacer »,
un etat loading et les erreurs serveur.

- [ ] Ecrire les tests React : etat sans CV, affichage du nom, selection,
  upload, remplacement, fichier invalide, erreur conservee et bouton bloque
  pendant la requete.
- [ ] Verifier le rouge avec `npm test -- --watchAll=false --runTestsByPath src/components/Candidatures/DefaultCvCard.test.jsx`.
- [ ] Implementer la carte en MUI 7 (`Grid size` si besoin), utiliser
  `FormData.append('fichier', file)` et recharger le nom depuis la reponse ;
  ne jamais afficher une URL publique du CV.
- [ ] Verifier le vert avec la meme commande et les tests `Parametres`.

### Task 5 : confirmation distincte, etats et reconciliation en frontend

**Fichiers :** modifier `frontend/src/pages/CandidatureDetail.jsx`,
`frontend/src/components/Candidatures/EmailBrouillonDialog.jsx`,
`frontend/src/services/api.js` et les tests correspondants.

**Interfaces :** `prepareEmailSend()` conserve le sens du lot 3 (passe a
`ready`, aucun Gmail). Les nouvelles methodes `sendEmail`,
`confirmEmailManually` et `createEmailRetry` appellent les trois routes de la
tache 3.

- [ ] Ecrire les tests React : « Preparer l'envoi » ne contacte pas Gmail ;
  un email `ready` ouvre un dialogue de confirmation montrant destinataire,
  objet et CV ; Annuler ferme sans appel ; Confirmer appelle `sendEmail`
  exactement une fois ; loading bloque le double clic ; succes affiche
  `sent` et recharge la timeline ; echec certain affiche `failed` et propose
  une nouvelle tentative ; issue incertaine affiche le message de
  verification et les deux actions explicites. Un `sending` recent sans
  erreur affiche seulement « Envoi en cours » ; apres 5 minutes, afficher
  les actions de reconciliation.
- [ ] Apres une reponse d'envoi perdue ou une erreur sans email serialise,
  relire le statut serveur. Ne jamais qualifier l'issue d'echec certain ni
  reproposer un envoi depuis un statut local potentiellement obsolete ; si la
  relecture echoue, bloquer ce bouton et offrir une actualisation explicite.
  Recharger aussi les metadonnees du CV a l'ouverture de la confirmation.
- [ ] Ajouter un test qui affiche deux tentatives `sent` liees (`retry_of`)
  et deux evenements d'historique, avec un avertissement de doublon.
- [ ] Verifier le rouge avec `npm test -- --watchAll=false --runTestsByPath src/pages/CandidatureDetail.test.jsx`.
- [ ] Renommer le bouton du brouillon en « Preparer l'envoi » pour ne pas le
  confondre avec le vrai envoi. Ajouter un dialogue distinct de confirmation
  pour `ready` et un dialogue d'avertissement avant duplication de
  `sending`. Garder l'email original visible apres duplication et ouvrir le
  nouveau `draft` dans la previsualisation/edition existante.
- [ ] Verifier le vert avec les tests de la page et du dialogue.

### Task 6 : verification globale, etat et commit

**Fichiers :** modifier `AGENTS.md` section 5 uniquement pour l'etat du lot.

- [ ] Lancer `..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
  et `..\venv\Scripts\python.exe manage.py test` depuis `backend/`.
- [ ] Lancer `npm test -- --watchAll=false` depuis `frontend/` et, si les
  composants ont change, `npm run build`.
- [ ] Verifier `git diff --check`, les fichiers non suivis et l'absence de
  `.env`, secrets, CV ou fichiers `media/` dans l'index.
- [ ] Mettre a jour `AGENTS.md` section 5 avec les routes, la limite
  `sending`/verification manuelle, la migration `0009`, les tests exacts et
  la validation OAuth reelle rapportee par l'utilisateur (sans pretendre
  avoir effectue un envoi reel de candidature).
- [ ] Relire le diff puis creer un commit coherent du lot 5. Aucun push sans
  demande explicite. Verifier `git status` apres commit.

## Limites explicites

- Le scope `gmail.send` ne permet pas de verifier automatiquement les
  messages envoyes. Une nouvelle tentative apres issue incertaine peut donc
  produire un vrai doublon ; l'interface avertit et exige un nouveau geste.
- Pour une eventuelle V2, ne pas supposer que `gmail.metadata` suffirait a
  retrouver un message precis : `messages.list` interdit son parametre de
  recherche `q` avec ce scope. Reevaluer alors les permissions necessaires.
- Aucun envoi en masse, LLM, relance automatique ni lecture Gmail en V1.
- Les tests simulent Gmail ; l'utilisateur devra confirmer ensuite l'envoi
  reel d'un email de test volontaire avant de considerer ce parcours valide
  en conditions reelles.
