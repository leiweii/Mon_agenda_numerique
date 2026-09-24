# AGENTS.md - Guide de reprise du projet

Ce fichier est le point d'entree pour un agent Codex ou pour une personne
qui decouvre le depot. Il doit rester court, vrai et actionnable. Les details
de conception longs vivent dans `docs/` ou `docs/superpowers/plans/`.

## 1. Projet en une minute

**Mon Agenda Numerique** est une application personnelle de gestion de taches.
Elle combine un backend Django REST, un frontend React/MUI et un module de
recommandations d'horaires avec appel Anthropic optionnel et repli local.

Le projet est fonctionnel en developpement local, mais il n'est pas pret pour
la production. Les principaux points non termines sont les statistiques de
compte reelles, l'alimentation automatique des habitudes, la configuration SMTP
de production et la configuration de deploiement.

Stack actuelle :

- Backend : Python, Django 6, Django REST Framework, PostgreSQL, token auth.
- Frontend : React 19, React Router 7, Material UI 7, Axios, Recharts, date-fns.
- IA : SDK `anthropic` cote Django, avec repli deterministe si aucune cle n'est disponible.

## 2. Carte rapide du code

- `backend/backend/settings.py` : configuration Django, base de donnees, CORS, apps.
- `backend/api/auth_backends.py` : authentification par e-mail ou nom d'utilisateur.
- `backend/api/authentication.py` : login, inscription, logout, utilisateur courant et reset de mot de passe.
- `backend/api/models.py` : taches, categories, candidatures, actions, preferences, statistiques, cache et journaux LLM.
- `backend/api/serializers.py` : contrats JSON exposes par l'API.
- `backend/api/views.py` : viewsets REST, statistiques, recommandations a regles et IA.
- `backend/api/candidature_scraper.py` : normalisation d'URL, telechargement
  HTTP securise et extraction HTML des offres d'emploi.
- `backend/api/candidature_llm.py` : repli Anthropic valide pour les imports
  d'offres que le scraper ne peut pas extraire.
- `backend/api/llm_service.py` : prompt, appel Anthropic, parsing et validation de reponse.
- `backend/api/llm_performance.py` : cache, quota, journalisation et purge LLM.
- `backend/api/agent_service.py` : boucle d'orchestration bornee, appel LLM,
  persistance des messages et creation des propositions d'ecriture.
- `backend/api/agent_tools.py` : tools de lecture et d'ecriture scopes par
  utilisateur pour les taches et candidatures.
- `backend/api/agent_retention.py` : expiration a 24 h et purge probabiliste
  des actions agent en attente.
- `backend/api/signals.py` : invalidation du cache de recommandation.
- `frontend/src/services/api.js` : client Axios et base URL locale.
- `frontend/src/context/AuthContext.jsx` : etat d'authentification React.
- `frontend/src/pages/` : pages principales (`Home`, `Login`, `Inscription`,
  `MotDePasseOublie`, `ReinitialiserMotDePasse`, `Parametres`).
- `frontend/src/components/Taches/` : liste, carte et formulaire de taches.
- `frontend/src/components/Categories/` : CRUD des categories.
- `frontend/src/components/Statistiques/` : dashboard et graphique de priorites.
- `frontend/src/components/Candidatures/` : formulaire, cartes, filtres,
  timeline d'actions et vue Kanban.
- `frontend/src/pages/Candidatures.jsx` et `CandidatureDetail.jsx` : liste,
  import, export et suivi detaille des candidatures.
- `frontend/src/components/RecommandationsIA.jsx` : carte de recommandation IA.
- `frontend/src/components/Agent/AgentChat.jsx` : fil de conversation, reprise
  de l'historique et confirmation ou annulation des actions proposees.
- `docs/llm-contract.md` : contrat prompt/reponse des recommandations.
- `docs/llm-cache-quota-logging.md` : architecture cache, quota et journalisation.
- `docs/superpowers/plans/2026-09-10-llm-cache-quota-logging.md` : plan de mise en oeuvre detaille du controle cache/quota/journaux.
- `docs/superpowers/specs/2026-09-10-authentification-complete-design.md` : conception de l'authentification complete.
- `docs/superpowers/plans/2026-09-10-authentification-complete.md` : plan d'execution de l'authentification complete.
- `docs/superpowers/plans/2026-09-13-suivi-candidatures.md` : conception et decoupage en lots du module de suivi des candidatures.
- `docs/superpowers/plans/2026-09-15-agent-planification.md` : conception,
  securite et decoupage en six lots de l'assistant de planification.

## 3. Commandes utiles

Backend, depuis la racine du depot :

```bash
python -m venv venv
venv\Scripts\activate
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
python manage.py test
```

Frontend :

```bash
cd frontend
npm install
npm start
npm test -- --watchAll=false
```

Serveurs locaux attendus :

- API Django : `http://localhost:8000`
- Frontend React : `http://localhost:3000`
- Base API frontend actuelle : `http://localhost:8000/api/`

## 4. Maniere de travailler dans ce depot

- Une tache fonctionnelle doit correspondre a un lot/commit coherent. Ne pas
  melanger une fonctionnalite, une refonte et une correction sans lien.
- Avant de modifier une zone, lire les fichiers concernes et les tests deja
  presents. Suivre les conventions locales plutot qu'introduire un style neuf.
- Pour un changement complexe, ne pas dupliquer toute la conception dans ce
  fichier. Creer ou mettre a jour un document dans `docs/` ou
  `docs/superpowers/plans/`, puis mettre ici seulement le lien et l'etat resume.
- S'arreter et demander confirmation avant toute decision architecturale :
  changement de backend d'authentification, modification de modele de donnees,
  migration touchant des donnees existantes, ou choix qui contraint durablement
  les interfaces backend/frontend.
- La section **Etat reel actuel** doit etre mise a jour a chaque lot/commit
  termine et teste. Elle ne doit pas etre reservee aux audits ponctuels, sinon
  elle redevient obsolete comme un ancien README.
- Ajouter ou adapter les tests au meme moment que le comportement modifie.
  Avant de declarer un lot termine, executer les tests backend et frontend
  pertinents, ou expliquer clairement ce qui n'a pas pu etre lance.
- Ne jamais ajouter de secret dans Git, le frontend, les tests ou la
  documentation. Les cles LLM restent cote backend via l'environnement.
- Ne pas modifier les migrations, dependances ou code applicatif pour une tache
  purement documentaire.
- Pour les nouveaux composants MUI, preferer l'API MUI 7 (`size`) plutot que
  l'ancienne API Grid (`item`, `xs`, `sm`, `md`) encore presente dans certains
  composants.
- Proteger les changements utilisateur existants : ne pas annuler des fichiers
  modifies sans demande explicite.

## 5. Etat reel actuel

Legende : `[x]` implemente et couvert par les tests presents ; `[~]` partiel ou
avec limite connue ; `[ ]` absent.

### Authentification

- [x] Connexion par e-mail ou nom d'utilisateur, deconnexion et utilisateur
  courant par token. Fichiers principaux : `backend/api/auth_backends.py`,
  `backend/api/authentication.py`,
  `frontend/src/context/AuthContext.jsx`, `frontend/src/pages/Login.jsx`.
- [x] Inscription utilisateur par e-mail : `POST /api/auth/register/`, username
  interne genere automatiquement, validation Django du mot de passe,
  confirmation de mot de passe, token retourne et session ouverte cote frontend.
- [x] Limitation des tentatives d'authentification : quotas DRF pour inscription,
  login, demande de reset et confirmation de reset ; le frontend remonte les
  erreurs `429` via le champ `detail`.
- [~] Mot de passe oublie et reinitialisation : endpoints et ecrans implementes,
  lien avec token Django, confirmation de mot de passe et tests presents. En
  production, la configuration SMTP reelle reste a fournir par environnement.

### Taches et categories

- [x] CRUD des taches avec titre, description, echeance, priorite, categorie,
  couleur, emoji et etat complete.
- [x] Filtres "aujourd'hui" et semaine ISO via les actions API correspondantes.
- [x] CRUD des categories personnalisees, scope par utilisateur.
- [x] Suppression d'une categorie avec conservation des taches associees via
  categorie nulle.

### Candidatures

- [x] Modele `Candidature` et migration initiale avec URL, titre,
  entreprise, description, type de poste, statut, source d'extraction,
  source du canal, tags Postgres, favori, archivage, CV utilise, dates limite
  et de relance, notes et contrainte unique `(utilisateur, url)`. Le lot 6
  ajoute `lieu` et le mode de travail facultatif (`sur_site`, `hybride`,
  `teletravail`).
- [x] API CRUD standard `/api/candidatures/` scopee par utilisateur, avec
  serializer DRF et tests backend de creation, valeurs par defaut et isolation
  par utilisateur.
- [x] Lot 2 : `POST /api/candidatures/import_url/` normalise l'URL (retrait
  du tracking et du fragment), detecte les doublons de l'utilisateur avant
  tout appel reseau et retourne `{duplicate: true, candidature_id}`.
  Sinon, `backend/api/candidature_scraper.py` extrait le titre et la
  description (Open Graph, puis HTML nettoye), sans sauvegarde automatique.
  Si le scraping est insuffisant, passage au repli LLM du lot 3.
- [x] Tests du scraping, criteres d'echec, doublons, isolation, validation
  d'URL et absence de sauvegarde. Telechargement HTTP(S) limite a 1 Mo,
  timeout socket de 6 s, adresses non publiques bloquees et connexion sur
  l'IP validee avec verification TLS du domaine. Les redirections ne sont
  pas suivies et JavaScript n'est pas execute.
- [x] Lot 3 : `backend/api/candidature_llm.py` reutilise l'appel Anthropic
  existant apres echec du scraping, avec le HTML deja telecharge (20 000
  caracteres maximum), traite comme donnees non fiables. JSON valide et
  types controles, titre/description requis, entreprise vide et type `autre`
  par defaut ; `source_extraction=llm` uniquement pour une extraction valide.
  Sans contenu recuperable, sans cle, si quota atteint ou si le LLM echoue,
  retour HTTP 200 avec formulaire vide et URL conservee, sans sauvegarde.
- [x] Quota d'import distinct : `CANDIDATURE_LLM_DAILY_LIMIT` configurable
  par environnement, 10 extractions LLM/jour/utilisateur par defaut (jour
  Django, actuellement UTC). Reservations atomiques ; les echecs LLM comptent,
  les doublons, succes scraping et absences de cle/contenu ne comptent pas.
  Migration `0004_journalappelllm_usage` : anciens journaux attribues aux
  recommandations, quotas independants et journalisation sans contenu brut.
  Tests du repli, de la validation JSON, des quotas et des acces concurrents.
- [x] Lot 4 : `CandidatureForm.jsx` et `CandidatureCard.jsx` dans
  `frontend/src/components/Candidatures/`, avec Grid MUI 7 (`size`). Formulaire
  de creation/edition couvrant tous les champs modifiables, dates facultatives,
  tags, favori et archivage ; metadonnees automatiques en lecture seule.
  Erreurs de sauvegarde visibles sans perdre la saisie, commandes bloquees
  pendant l'enregistrement, suppression avec confirmation.
- [x] `frontend/src/pages/Candidatures.jsx` : lien et analyse, apercu editable,
  repli manuel, gestion des erreurs, ajout manuel, liste groupee par statut
  et compteur. Route protegee directe `/candidatures`.
  Un doublon ouvre la candidature existante en edition rapide. Client
  `candidaturesAPI` dans `frontend/src/services/api.js`.
  Tests frontend et parcours navigateur 390/1440 px avec API simulee.
  Verification lot 4 : 57 tests / 21 suites reussis. Build reussi avec
  l'avertissement de dependance de hook deja present dans `TacheListe.jsx`.
- [x] Lot 5 : entree `Candidatures` dans la navigation principale et barre de
  filtres `CandidatureFiltres.jsx`. Recherche, statut, type de poste, canal,
  tags, favori, archives, dates d'ajout et limite, relances dues et tri sont
  refletes dans l'URL. Les archives sont masquees par defaut.
- [x] `GET /api/candidatures/` applique les filtres et tris autorises en restant
  scope par utilisateur. `PATCH /api/candidatures/{id}/archiver/` archive une
  candidature sans la supprimer. Verification lot 5 : 120 tests backend et
  63 tests frontend (22 suites) reussis.
- [x] Lot 6 : migration `0005` avec `ActionCandidature`, date metier distincte
  de la date de creation et historique ordonne par date decroissante. CRUD
  imbrique des actions, scope par utilisateur et rattachement au parent impose
  par l'URL.
- [x] Page protegee `/candidatures/:id` avec informations generales, edition
  complete, statut/favori/tags modifiables directement, archivage, suppression,
  timeline et formulaire d'ajout/edition d'action. Les cartes ouvrent le detail.
  Verification lot 6 : 126 tests backend et 67 tests frontend (24 suites),
  parcours navigateur 390/1440 px sans erreur ni debordement.
- [x] Lot 7 : vue `CandidatureKanban.jsx` avec cinq colonnes de statut,
  cartes compactes, glisser-deposer accessible et mise a jour par
  `PATCH /api/candidatures/{id}/`. La bascule Liste/Kanban reste locale a la
  page et les deux vues partagent les candidatures issues des filtres actifs.
  Dependance `@hello-pangea/dnd` 18.0.1. Verification lot 7 : 71 tests
  frontend (25 suites) reussis.
- [x] Lot 8 : `GET /api/candidatures/export_csv/` exporte les candidatures
  scopees par utilisateur avec les memes filtres et tris que la liste. Le
  fichier UTF-8 avec BOM contient les onze colonnes documentees, avec les tags
  joints par `;` et les cellules de type formule neutralisees. Le bouton
  `Exporter en CSV` transmet les filtres actifs et declenche le telechargement
  cote navigateur. Verification lot 8 : 128 tests
  backend reussis ; 14 tests frontend concernes (2 suites) reussis.
- [x] Verification finale du module : 129 tests backend et 72 tests frontend
  (25 suites) reussis. La commande Jest du projet s'execute en serie pour
  eviter les timeouts MUI/JSDOM lies a la saturation des workers. Le graphe
  des migrations `api` est coherent et aucun changement de modele non migre
  n'est detecte. Les migrations `0003` a `0005` restent a appliquer sur la
  base locale avec `python manage.py migrate`.
- [x] Redesign de `/candidatures` sur une branche isolee issue de `main` :
  compteurs calcules sur les candidatures affichees, recherche principale,
  filtres detailles repliables et cartes en une colonne. Ajout manuel, import
  URL, export CSV, selection multiple et Kanban restent disponibles. La liste
  API expose `email_status` depuis le dernier `EmailCandidature` (tri
  `created_at`, puis `id` decroissants) ; `null` est affiche « A preparer ».
  Les tags restent des tags ; aucune stack n'est deduite, et aucune migration
  n'est necessaire. Pour ajouter une stack plus tard, prevoir un champ explicite
  de technologies avec migration, formulaire et API. « En cours » compte les
  statuts `postule` et `entretien` ; « Echeance sous 7 jours » reprend la plage
  du filtre existant. « A relancer » garde exactement la regle actuelle
  `date_relance <= aujourd'hui`, meme pour `accepte` ou `refuse`. Amelioration
  ulterieure a valider separement : exclure ces statuts terminaux des relances.
  Verification : 243 tests backend et 126 tests frontend (31 suites) reussis,
  build frontend reussi avec l'avertissement preexistant dans `TacheListe.jsx`,
  `makemigrations --check --dry-run` sans changement.

### Emails de candidature

- [x] Lot 1 : modeles `EmailCandidature` et `CVUtilisateur`, avec migration
  `api.0007`. Une candidature peut conserver plusieurs emails, scopes par le
  proprietaire de la candidature. Les statuts `draft`, `ready`, `sending`,
  `sent`, `failed` et `cancelled` sont disponibles, avec `draft` par defaut.
  Un seul CV par defaut est autorise par utilisateur en V1. Verification :
  162 tests backend reussis, dont 5 tests dedies au lot ; `api.0007` est
  appliquee sur la base locale.
- [x] Lot 2 : `backend/api/email_candidature_service.py` remplace les variables
  entreprise, contact, civilite, poste, formation, portfolio et GitHub dans le
  template deterministe. Si le nom ou la civilite manque, la salutation devient
  `Bonjour Madame, Monsieur`. `POST /api/candidatures/{id}/preparer_email/`
  cree un `EmailCandidature` au statut `draft`, scope par l'utilisateur, sans
  appel Gmail ni connexion reseau. Verification : 169 tests backend reussis,
  dont 12 tests du module email et 7 ajoutes pour ce lot.
- [x] Lot 3 : la page detail d'une candidature permet de preparer, consulter
  et editer le destinataire, l'objet et le message d'un brouillon. Elle affiche
  le nom du CV par defaut. `Enregistrer` persiste les modifications ; `Annuler`
  passe le brouillon a `cancelled` ; `Envoyer` persiste les modifications et
  passe le brouillon a `ready`, sans envoyer d'email. Les endpoints sont scopes
  par le proprietaire de la candidature et les statuts terminaux ne sont pas
  modifiables. Verification du lot : 174 tests backend et 82 tests frontend
  (27 suites) reussis.
- [x] Lot 4 : OAuth 2.0 Gmail dans les Parametres avec bouton de connexion,
  `state` a usage unique (10 minutes), PKCE S256 et scope `gmail.send`.
  Migration `api.0008` : `ConnexionGmail` stocke uniquement le refresh token
  chiffre et `TentativeOAuthGmail` protege le retour OAuth. Les quatre routes
  `/api/gmail/` couvrent connexion, callback, statut et verification ; un token
  expire est renouvelle, un token revoque demande une reconnexion. Variables
  backend requises : `GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET`,
  `GMAIL_OAUTH_REDIRECT_URI`, `GMAIL_TOKEN_ENCRYPTION_KEY` (jamais commitees).
  Tests Google entierement mocks : 193 tests backend et 87 tests frontend
  (28 suites) reussis ; `api.0008` appliquee sur la base locale. Aucun envoi
  d'email dans ce lot. L'utilisateur a ensuite valide le flux OAuth reel avec
  son compte Google jusqu'au retour dans les Parametres (compte connecte).
- [x] Lot 5 : upload/remplacement du CV PDF par defaut dans les Parametres
  (`GET, PUT /api/candidatures/cv_par_defaut/`, 5 Mio maximum, fichier prive)
  et envoi individuel via `POST /api/candidatures/{id}/emails/{email_id}/envoyer/`.
  Le brouillon doit d'abord etre `ready`, puis l'utilisateur confirme l'envoi
  dans un dialogue distinct. Adresse expediteur du compte applicatif validee
  (identique au Gmail connecte ou alias autorise), CV et connexion revalides
  cote serveur. L'empreinte du CV presente a la confirmation doit correspondre
  aux octets joints ; un remplacement exige une nouvelle confirmation. La
  transition `ready -> sending` est reservee en base avant
  l'appel Gmail ; un double POST n'envoie pas deux fois le meme email.
  Un succes Gmail avec id devient `sent` et cree une action d'historique ; un
  echec certain devient `failed`. En cas de resultat incertain, l'email reste
  `sending` sans renvoi automatique. Apres erreur explicite ou cinq minutes
  d'attente calculees a l'affichage, l'utilisateur peut confirmer manuellement
  (`confirmer_manuellement/`) ou creer un nouveau brouillon lie par `retry_of`
  (`nouvelle_tentative/`), avec avertissement du risque de doublon. Migration
  `api.0009` cree les metadonnees de reconciliation et la chaine lineaire de
  tentatives ; elle est appliquee sur la base locale (`showmigrations` :
  `[X] 0009`).
  Si la reponse HTTP de l'envoi est perdue, le frontend relit le statut serveur
  et bloque tout nouvel envoi si cette verification echoue.
  Tests Gmail/HTTP entierement mocks : 226 tests backend et 111 tests frontend
  (29 suites) reussis ; build frontend reussi. Verification corrective avant
  fusion : les 111 tests passent avec `npm test -- --watchAll=false` depuis le
  worktree visible, sans reglage CI manuel. Le script npm lance CRA en serie et
  en mode CI pour que PowerShell execute toute la suite meme si `npm.ps1` ne
  transmet pas les options apres `--`. Les tests d'envoi attendent la fermeture
  effective du dialogue MUI avant de chercher les actions de la page.
  Le lot 5 a ete valide manuellement par l'utilisateur avant la fusion. En mode
  Google Testing, le refresh token peut expirer apres sept jours et exiger une
  reconnexion.
- [x] Lot 6 : selection multiple dans la liste des candidatures et
  `POST /api/candidatures/preparer_emails/` pour creer un brouillon `draft`
  independant par candidature. Chaque destinataire et contact est saisi
  separement ; les champs de formation et liens sont partages. La validation
  de toutes les lignes et du proprietaire de chaque candidature precede une
  creation atomique : en cas d'erreur, aucune ligne n'est creee et l'interface
  designe chaque candidature concernee. Un brouillon deja existant n'empeche
  pas la creation d'un nouveau brouillon distinct. Le resultat liste les
  brouillons et propose seulement leur ouverture individuelle dans un nouvel
  onglet, directement sur le bon brouillon ; aucun envoi groupe, CC ou BCC.
  Aucune migration supplementaire. Verification lot 6 :
  237 tests backend et 115 tests frontend (29 suites) reussis avec
  `npm test -- --watchAll=false`. Build frontend reussi avec le seul
  avertissement de hook preexistant dans `TacheListe.jsx` ; aucune migration
  de modele detectee. Les lots 5 et 6 ont ete fusionnes sur `main` par deux
  merges classiques sans conflit manuel ni squash. Verification de `main`
  apres fusion : 238 tests backend et 117 tests frontend (30 suites) reussis
  avec `npm test -- --watchAll=false`. Aucun push n'a ete effectue.
  Correction apres essai manuel : le backend sur `main` utilisait encore la
  base locale au schema `api.0008`, d'ou une erreur SQL de colonne absente
  pendant la preparation en masse. `api.0009` a ete appliquee ; un test de
  regression reproduit l'echec avant migration puis le succes apres migration.
  En cas d'erreur serveur, le frontend indique de verifier les brouillons
  existants avant de reessayer, ainsi que le terminal backend et les migrations.
  Verification apres correction : 239 tests backend et 118 tests frontend
  (30 suites) reussis. Une passe frontend intermediaire a eu cinq expirations
  intermittentes a 5 s dans `CandidatureDetail.test.jsx`, non modifie ; cette
  suite a ensuite passe seule (26/26), puis la suite complete a passe (118/118).

### Preferences et interface

- [x] Preferences utilisateur persistantes : heures productives, theme clair/sombre
  et notifications.
- [x] Chargement du theme sauvegarde au demarrage, avec normalisation des anciennes
  valeurs `auto`.
- [~] Responsive partiel : `Home`, `Parametres` et `Dashboard` ont ete adaptes et
  testes ; `TacheForm.jsx` et les composants de categories utilisent encore
  l'ancienne API Grid MUI.
- [~] Statistiques de compte dans `Parametres.jsx` : valeurs de demonstration
  calculees dans le frontend, sans donnees API reelles.

### Dashboard et statistiques

- [x] Endpoint `GET /api/taches/statistiques/` avec total, taux de completion et
  repartition des priorites 1 a 4, zeros inclus.
- [x] Graphique Recharts des priorites integre au dashboard.

### Recommandations

- [~] `GET /api/taches/meilleur_moment/` existe et respecte le contrat
  `{heures_recommandees, message}`. Limite connue : les statistiques
  d'utilisation ne sont pas alimentees automatiquement lors de la completion
  normale d'une tache.
- [x] `GET /api/taches/recommandation_ia/` appelle le service LLM quand c'est
  possible et garantit le meme contrat JSON en cas de succes, d'erreur ou de
  repli local.
- [x] Cache persistant 24 h, quota quotidien par utilisateur, journalisation
  pseudonymisee et purge probabiliste des anciens journaux. Details dans
  `docs/llm-cache-quota-logging.md` et plan d'execution dans
  `docs/superpowers/plans/2026-09-10-llm-cache-quota-logging.md`.
- [x] Frontend `RecommandationsIA.jsx` avec etats chargement, succes, erreur et
  action de nouvel essai.

### Agent personnel de planification

- [x] Lot 1 : modeles `ConversationAgent`, `MessageAgent` et
  `ActionEnAttente`, avec migration `api.0006`. Les tools de lecture
  `get_today_tasks(user)` et `get_applications(user)` sont disponibles dans
  `backend/api/agent_tools.py` et appliquent un scoping strict par utilisateur ;
  les candidatures archivees sont exclues et la date de derniere action est
  incluse. Verification lot 1 : 134 tests backend reussis.
- [x] Lot 2 : `backend/api/agent_service.py` fournit une boucle bornee a cinq
  etapes, transmet la date locale au LLM, persiste les messages et retourne le
  message de repli documente si elle ne conclut pas. `POST /api/agent/chat/`
  cree ou reprend une conversation scopee par utilisateur. Seuls les deux tools
  de lecture du lot 1 sont exposes. Verification lot 2 : 141 tests backend
  reussis. Conception et lots suivants :
  `docs/superpowers/plans/2026-09-15-agent-planification.md`.
- [x] Lot 3 : tools `create_task` et `update_task` scopes par utilisateur,
  avec erreur explicite pour une categorie inexistante ou appartenant a un
  autre utilisateur. Une demande d'ecriture cree une `ActionEnAttente` et
  arrete la boucle sans modifier la tache. Les endpoints `confirmer/` et
  `annuler/` verrouillent et rechargent l'action cote serveur, verifient son
  proprietaire et son statut, puis utilisent exclusivement les arguments
  stockes ; le corps de confirmation ou d'annulation est ignore. Verification
  lot 3 : 152 tests backend reussis.
- [ ] Lot 4 non commence : aucun quota agent ni protection anti-injection
  dediee. La gestion d'erreur des tools reste aussi a implementer.
- [x] Lot 5 : page protegee `/agent` et entree `Assistant` dans la navigation.
  `AgentChat.jsx` affiche le fil sous forme de bulles et les resultats d'outils
  sous forme de resumes lisibles, sans JSON brut. La saisie est bloquee pendant
  la generation. Les cartes d'action en attente envoient uniquement l'id aux
  endpoints de confirmation ou d'annulation. L'id de conversation recente est
  conserve cote navigateur et son historique, scope par utilisateur, est
  recharge via `GET /api/agent/conversations/{id}/`. Verification lot 5 :
  154 tests backend et 77 tests frontend (26 suites) reussis.
- [x] Lot 6 : les `ActionEnAttente` encore en attente depuis plus de 24 heures
  passent au statut `expiree` avec leur date de traitement. Comme pour les
  journaux LLM, une purge probabiliste est declenchee par les requetes agent et
  ses erreurs ne bloquent pas la requete. Les endpoints de confirmation et
  d'annulation recontrolent aussi le delai sous verrou afin qu'une action
  expiree ne puisse jamais etre executee. Verification lot 6 : 156 tests
  backend reussis. La migration `api.0006` est appliquee sur la base locale.
- [~] Verification globale : 157 tests backend et 77 tests frontend (26 suites)
  reussis. Le parcours automatise couvre les deux tools de lecture, la creation
  confirmee et l'annulation sans creation. Le test de falsification confirme
  toujours que le backend ignore les arguments envoyes par le client. Aucun
  changement de modele non migre n'est detecte et `api.0006` est appliquee sur
  la base locale. L'ensemble des six lots ne peut pas etre declare termine tant
  que le lot 4 reste absent.

### Configuration et production

- [~] Configuration locale fonctionnelle avec PostgreSQL, CORS local et URL Axios
  locale.
- [~] Non pret production : `DEBUG=True`, `SECRET_KEY` codee en dur, URL API
  locale et configuration SMTP doivent etre externalises ou securises avant
  deploiement.

## 6. Contrats a ne pas casser

Reponse de recommandation, quelle que soit la source :

```json
{
  "heures_recommandees": [9, 14],
  "message": "Une recommandation concise."
}
```

Routes API principales, toutes prefixees par `/api/` :

- `POST /auth/login/`, `POST /auth/register/`, `POST /auth/logout/`, `GET /auth/user/`
- `POST /auth/mot-de-passe-oublie/`, `POST /auth/reinitialiser-mot-de-passe/`
- `/taches/`, `/taches/{id}/`, `/taches/aujourd_hui/`, `/taches/cette_semaine/`
- `/taches/statistiques/`, `/taches/meilleur_moment/`, `/taches/recommandation_ia/`
- `/candidatures/`, `/candidatures/{id}/`
- `GET /candidatures/` inclut `email_status` nullable dans chaque element ;
  les autres routes de candidature conservent leur contrat existant.
- `POST /candidatures/import_url/`
- `PATCH /candidatures/{id}/archiver/`
- `GET /candidatures/cv_par_defaut/`
- `POST /candidatures/{id}/preparer_email/`, `GET /candidatures/{id}/emails/`
- `POST /candidatures/preparer_emails/` (preparation atomique, sans envoi)
- `PATCH /candidatures/{id}/emails/{email_id}/`
- `POST /candidatures/{id}/emails/{email_id}/annuler/`
- `POST /candidatures/{id}/emails/{email_id}/preparer_envoi/` (`ready`, sans envoi)
- `GET, POST /candidatures/{id}/actions/`
- `GET, PUT, PATCH, DELETE /candidatures/{id}/actions/{action_id}/`
- `/categories/`, `/categories/{id}/`
- `/preferences/`, `/preferences/{id}/`
- `POST /agent/chat/`, `GET /agent/conversations/{id}/`
- `POST /agent/actions/{id}/confirmer/`, `POST /agent/actions/{id}/annuler/`

Routes frontend protegees : `/candidatures`, `/candidatures/:id` et `/agent`.

## 7. Verification attendue

Pour un changement backend :

```bash
cd backend
python manage.py test
```

Pour un changement frontend :

```bash
cd frontend
npm test -- --watchAll=false
```

Pour un changement documentaire seul, relire le rendu Markdown et verifier que
les chemins cites existent. Les tests applicatifs ne sont pas obligatoires si
aucun comportement, dependance ou contrat n'a change.
