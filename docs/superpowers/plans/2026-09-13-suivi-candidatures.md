# Suivi des candidatures - Document de conception

Statut : lots 1 a 8 implementes. L'etat teste et les limites actuelles sont
resumes dans `AGENTS.md` section 5.

## 1. Objectif

Ajouter un module permettant d'enregistrer des offres d'emploi de tout type
(stage, alternance, CDI, CDD, freelance, ou autre) a partir d'un lien colle
par l'utilisateur, avec remplissage automatique du titre, de l'entreprise et
de la description, puis de suivre le statut de chaque candidature dans le
temps.

Ce module est independant du systeme de taches existant. Il ne modifie ni le
modele `Tache`, ni les contrats de recommandation deja documentes dans
`docs/llm-contract.md`.

## 2. Perimetre

Inclus dans ce lot :

- Nouveau modele `Candidature` (avec favori, tags, source du canal,
  archivage, CV utilise, date de relance) et migration associee.
- Endpoint d'import par URL avec detection de doublon et extraction
  automatique (scraping d'abord, repli LLM en cas d'echec ou de resultat
  insuffisant).
- CRUD standard des candidatures, y compris archivage dedie.
- Historique d'actions (`ActionCandidature`) pour suivre les relances et
  entretiens dans le temps.
- Page liste avec filtres avances, page de detail, navigation dediee.
- Vue Kanban alternative a la liste.
- Export CSV.

Explicitement hors perimetre pour ce lot :

- Rappels ou notifications automatiques (push/email) sur les dates limites
  ou de relance - le champ `date_relance` existe et est filtrable, mais
  aucune notification active n'est envoyee dans ce lot.
- Statistiques dediees aux candidatures (pourrait reprendre plus tard le
  meme pattern que `taches/statistiques/`).
- Import en masse ou synchronisation automatique avec un site tiers.
- Upload reel de fichiers CV/lettre de motivation (le champ `cv_utilise`
  reste un texte libre, pas un fichier stocke).

## 3. Modele de donnees

Nouveau modele dans `backend/api/models.py`, scope par utilisateur comme
`Tache` et `Categorie` :

```python
from django.contrib.postgres.fields import ArrayField


class Candidature(models.Model):
    class TypePoste(models.TextChoices):
        STAGE = "stage", "Stage"
        ALTERNANCE = "alternance", "Alternance"
        CDI = "cdi", "CDI"
        CDD = "cdd", "CDD"
        FREELANCE = "freelance", "Freelance"
        AUTRE = "autre", "Autre"

    class Statut(models.TextChoices):
        A_POSTULER = "a_postuler", "A postuler"
        POSTULE = "postule", "Postule"
        ENTRETIEN = "entretien", "Entretien"
        REFUSE = "refuse", "Refuse"
        ACCEPTE = "accepte", "Accepte"

    class SourceCanal(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        INDEED = "indeed", "Indeed"
        WELCOME_JUNGLE = "welcome_jungle", "Welcome to the Jungle"
        SITE_DIRECT = "site_direct", "Site de l'entreprise"
        COOPTATION = "cooptation", "Cooptation / reseau"
        AUTRE = "autre", "Autre"

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="candidatures")
    url = models.URLField(max_length=1000)
    titre = models.CharField(max_length=255)
    entreprise = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    type_poste = models.CharField(max_length=20, choices=TypePoste.choices, default=TypePoste.AUTRE)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.A_POSTULER)
    source_extraction = models.CharField(max_length=20, blank=True)  # "scraping" ou "llm"
    source_canal = models.CharField(max_length=20, choices=SourceCanal.choices, default=SourceCanal.AUTRE)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    favori = models.BooleanField(default=False)
    archive = models.BooleanField(default=False)
    cv_utilise = models.CharField(max_length=255, blank=True)  # ex. "CV_v3_dev.pdf", texte libre
    date_limite = models.DateField(null=True, blank=True)
    date_relance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["utilisateur", "url"], name="unique_url_par_utilisateur")
        ]
```

Remarques :

- `source_extraction` sert uniquement a l'observabilite (savoir si le
  scraping a suffi ou si le repli LLM a ete necessaire), pas a la logique
  metier. `source_canal` est different : c'est une information saisie/deduite
  pour savoir par quel canal l'offre a ete trouvee.
- `tags` utilise `django.contrib.postgres.fields.ArrayField`, disponible car
  le projet est deja sur PostgreSQL. Alternative si on prefere eviter un champ
  specifique a PostgreSQL : modele `Tag` separe avec relation ManyToMany. Le
  choix ArrayField est plus simple pour ce volume de donnees (usage personnel,
  pas de recherche cross-utilisateur sur les tags).
- La contrainte `unique_url_par_utilisateur` empeche au niveau base de donnees
  qu'un meme utilisateur enregistre deux fois la meme URL. C'est une securite
  en dernier recours : la detection de doublon cote applicatif (section 4)
  doit intervenir avant, avec un message clair, plutot que de laisser
  remonter une erreur d'integrite brute a l'utilisateur.
- `cv_utilise` reste un champ texte libre (pas d'upload de fichier reel dans
  ce lot) : l'utilisateur note lui-meme quelle version il a envoyee.

## 4. Strategie d'extraction

Decision retenue : **scraping d'abord, repli LLM si echec ou resultat
insuffisant**, pour limiter le cout et la dependance au SDK `anthropic`.

### Etape 1 - Scraping

Nouveau module `backend/api/candidature_scraper.py` :

1. Requete HTTP GET sur l'URL fournie avec un timeout court (ex. 6s) et un
   User-Agent explicite.
2. Extraction des balises `<meta property="og:title">`,
   `<meta property="og:description">`, a defaut `<title>` et le premier bloc
   de texte significatif du corps de la page.
3. Nettoyage minimal (suppression des scripts/styles, normalisation des
   espaces).

Criteres d'echec qui declenchent le repli LLM :

- Statut HTTP different de 200, ou timeout/exception reseau.
- Titre absent ou trop court (< 3 caracteres) apres extraction.
- Description absente ou manifestement generique (ex. texte de cookie banner,
  moins de 40 caracteres utiles).

### Etape 2 - Repli LLM (si necessaire)

Reutilisation du pattern deja existant dans `backend/api/llm_service.py` :
meme mecanisme d'appel Anthropic, meme gestion de cle absente (dans ce cas,
si le scraping a echoue ET que le LLM n'est pas disponible, l'utilisateur
recoit un formulaire vide a remplir manuellement, sans erreur bloquante).

Le contenu brut recupere a l'etape 1 (meme partiel) est transmis au LLM avec
un prompt demandant une extraction strictement structuree :

```json
{
  "titre": "...",
  "entreprise": "...",
  "description": "...",
  "type_poste": "stage | alternance | cdi | cdd | freelance | autre"
}
```

Le parsing et la validation de cette reponse suivent le meme niveau de
rigueur que celui deja applique aux recommandations dans
`llm_service.py` (validation du JSON, valeurs par defaut si champ manquant,
pas de confiance aveugle dans la sortie du modele).

### Etape 0 - Detection de doublon (avant tout scraping)

Des reception de l'URL dans `import_url/`, avant tout appel reseau ou LLM :
verifier si une `Candidature` existe deja pour cet utilisateur avec cette
meme `url` (normalisee : suppression des parametres de tracking type
`?utm_...` avant comparaison). Si oui, retourner directement
`{"duplicate": true, "candidature_id": <id>}` sans re-scraper. Le frontend
redirige alors vers la page de detail existante plutot que d'ouvrir un
formulaire de creation.

### Cout et quota

A confirmer avec l'utilisateur avant implementation : faut-il rattacher cet
appel au meme quota quotidien que `recommandation_ia`, ou un quota separe
dedie aux imports de candidature ? Recommandation : quota separe, car les
deux usages n'ont pas la meme frequence attendue.

## 5. Endpoints API

Prefixe `/api/`, ViewSet DRF suivant le style des routes existantes :

| Methode | Route | Description |
| --- | --- | --- |
| POST | `/candidatures/import_url/` | Recoit `{url}`, retourne soit les champs extraits **sans sauvegarder**, soit `{duplicate: true, candidature_id}` si l'URL existe deja |
| GET, POST | `/candidatures/` | Liste (filtrable, voir section 10.3) ou creation directe |
| GET, PUT, PATCH, DELETE | `/candidatures/{id}/` | Consultation, modification ou suppression |
| PATCH | `/candidatures/{id}/archiver/` | Bascule `archive` a `true` sans supprimer la ligne (action dediee plutot qu'un PATCH generique, pour rester explicite dans les logs et le frontend) |
| GET | `/candidatures/export_csv/` | Genere et retourne un CSV de toutes les candidatures de l'utilisateur courant, respecte les memes filtres que `GET /candidatures/` si fournis en query params |

`import_url/` ne sauvegarde jamais automatiquement : l'utilisateur valide ou
corrige l'apercu avant l'appel `POST /candidatures/`. Ce choix evite de
polluer la base avec des extractions ratees.

Colonnes du CSV d'export : `titre`, `entreprise`, `type_poste`, `statut`,
`source_canal`, `tags` (jointes par `;`), `favori`, `date_limite`,
`date_relance`, `date_ajout`, `url`. Encodage UTF-8 avec BOM pour une
ouverture correcte dans Excel.

## 6. Frontend

Nouveaux fichiers, en suivant l'organisation existante
(`frontend/src/components/Candidatures/`, page dediee dans
`frontend/src/pages/`) :

- `Candidatures.jsx` (page) : champ de collage de lien + bouton "Analyser",
  liste des candidatures groupees par statut.
- `CandidatureForm.jsx` : formulaire d'apercu/edition avant sauvegarde,
  reutilisable pour la creation manuelle et pour l'edition ulterieure.
- `CandidatureCard.jsx` : carte affichant titre, entreprise, type de poste,
  statut (badge colore), lien vers l'annonce originale.

Utiliser l'API MUI 7 (`size`) plutot que l'ancienne API Grid, conformement a
la regle deja en place dans `AGENTS.md` section 4.

Etats a gerer dans `Candidatures.jsx` : chargement de l'analyse du lien,
succes avec apercu editable, echec du scraping et du LLM (formulaire vide a
completer manuellement), sauvegarde en cours, erreur de sauvegarde.

## 7. Tests attendus

Backend (`backend/api/tests/`) :

- Modele `Candidature` : creation, valeurs par defaut, scoping par
  utilisateur.
- `candidature_scraper.py` : extraction reussie sur un HTML de test simple,
  detection correcte des criteres d'echec (statut HTTP, titre absent,
  description trop courte).
- Endpoint `import_url/` : cas scraping suffisant, cas repli LLM, cas echec
  complet (formulaire vide, pas d'exception non geree).
- CRUD standard des candidatures avec isolation par utilisateur.

Frontend :

- `CandidatureForm.jsx` : rendu et soumission avec donnees pre-remplies.
- `Candidatures.jsx` : etats de chargement/succes/erreur de l'analyse de
  lien.

## 8. Points necessitant confirmation avant implementation

Conformement a la regle de `AGENTS.md` section 4 (s'arreter avant toute
decision architecturale), les points suivants sont a valider :

1. Nouveau modele de donnees `Candidature` et migration associee - confirme
   par ce document si validation donnee par l'utilisateur.
2. Quota LLM separe ou partage avec `recommandation_ia` (section 4).
3. Politique de securite du scraping : whitelist de domaines, limite de
   taille de reponse HTTP, protection contre les URL internes/privees (SSRF)
   avant d'exposer `import_url/` publiquement.
4. Duree de conservation des candidatures archivees : conservation
   indefinie par defaut (recommande, l'archivage suffit a les sortir de la
   vue active), ou purge automatique apres un delai comme pour les journaux
   LLM ?
5. Contrainte unique `(utilisateur, url)` au niveau base de donnees
   (section 3) : validee par defaut avec ce document, sauf si l'utilisateur
   anticipe un cas legitime de doublon volontaire (ex. reposter la meme
   offre suivie separement).
6. Ajout de la dependance frontend `@hello-pangea/dnd` (ou equivalent) pour
   la vue Kanban (section 12) - premiere nouvelle dependance de ce module,
   a valider explicitement avant `npm install`.

## 9. Estimation de decoupage en lots

1. Modele + migration + CRUD basique, y compris les nouveaux champs
   (`favori`, `tags`, `source_canal`, `archive`, `cv_utilise`,
   `date_relance`) et la contrainte unique (sans extraction automatique).
2. Scraper + endpoint `import_url/` avec detection de doublon (scraping
   seul, sans LLM).
3. Repli LLM sur `import_url/` + quota associe.
4. Frontend complet (formulaire avec tous les champs, liste, etats).
5. Page dediee + navigation + filtres avances (section 10).
6. Historique d'actions et page de detail (section 11).
7. Vue Kanban (section 12) - sous reserve de validation de la dependance
   (point 6, section 8).
8. Export CSV (section 13).

## 10. Page dediee et navigation

### 10.1 Entree de navigation

Ajouter un lien "Candidatures" dans le composant de navigation principal
(equivalent de ce qui existe deja pour acceder a `Home` et `Parametres`),
pointant vers une nouvelle route `/candidatures`.

Deux sous-routes React Router 7 :

- `/candidatures` : page liste (section 10.2).
- `/candidatures/:id` : page de detail (section 11).

### 10.2 Page liste (`Candidatures.jsx`)

Structure de haut en bas :

1. **Barre d'ajout** : champ pour coller un lien + bouton "Analyser" (flux
   decrit section 4), et un bouton secondaire "Ajouter manuellement" qui
   ouvre directement `CandidatureForm` vide.
2. **Barre de filtres et recherche** (section 10.3).
3. **Compteur resume** : ex. "12 candidatures - 5 en attente, 3 entretiens,
   2 refus, 2 acceptees". Reutilise les memes statuts que le modele, calcule
   cote frontend a partir de la liste chargee (pas besoin d'un endpoint
   statistiques dedie pour ce lot).
4. **Liste des candidatures** : une `CandidatureCard` par element, cliquable
   vers `/candidatures/:id`. Chaque carte affiche titre, entreprise, type de
   poste (badge), statut (badge colore), date d'ajout, et date limite si
   definie et proche (mise en evidence si echeance sous 7 jours).

### 10.3 Filtres et recherche

Tous les filtres sont combinables (ET logique) et refletes dans les
parametres d'URL (`?statut=postule&type_poste=stage`) pour permettre de
partager ou rafraichir une vue filtree sans la perdre.

| Filtre | Type | Detail |
| --- | --- | --- |
| Recherche texte | champ libre | recherche sur `titre` et `entreprise`, cote frontend si le volume reste faible, sinon via un parametre `?search=` cote API |
| Statut | choix multiple | correspond aux valeurs de `Statut` (section 3), affichage en chips |
| Type de poste | choix multiple | correspond aux valeurs de `TypePoste` |
| Source du canal | choix multiple | correspond aux valeurs de `SourceCanal` |
| Tags | choix multiple | liste construite dynamiquement a partir des tags deja utilises par l'utilisateur |
| Favori uniquement | interrupteur | filtre `favori=true` |
| Inclure les archivees | interrupteur, desactive par defaut | par defaut la liste exclut `archive=true` ; cet interrupteur les reaffiche |
| Date d'ajout | plage de dates | filtre sur `date_ajout` |
| Date limite | option "echeance sous 7 jours" | raccourci utile plutot qu'une plage complete |
| A relancer | option "relance depassee ou du jour" | filtre `date_relance <= aujourd'hui`, met en avant les candidatures a relancer |
| Tri | select | par date d'ajout (defaut, plus recent d'abord), par date limite, par date de relance, par statut |

Endpoint concerne : `GET /candidatures/` accepte les query params `statut`,
`type_poste`, `source_canal`, `tags`, `favori`, `archive`, `search`,
`date_ajout_min`, `date_ajout_max`, `relance_due`, `ordering`. Par defaut
(sans le parametre `archive=true`), la liste exclut les candidatures
archivees. Filtrage cote backend via `django_filter` ou des query params
manuels geres dans le ViewSet, a trancher selon ce qui est deja utilise
ailleurs dans `views.py` (rester coherent avec le style existant, cf.
`AGENTS.md` section 4).

## 11. Detail d'une candidature et historique d'actions

### 11.1 Nouveau modele `ActionCandidature`

Une candidature evolue dans le temps : relance, entretien, etc. Cela merite
un historique plutot qu'un simple champ `notes`.

```python
class ActionCandidature(models.Model):
    class TypeAction(models.TextChoices):
        CANDIDATURE_ENVOYEE = "envoyee", "Candidature envoyee"
        RELANCE = "relance", "Relance"
        ENTRETIEN_TEL = "entretien_tel", "Entretien telephonique"
        ENTRETIEN_VISIO = "entretien_visio", "Entretien visio"
        ENTRETIEN_PRESENTIEL = "entretien_presentiel", "Entretien presentiel"
        TEST_TECHNIQUE = "test_technique", "Test technique"
        OFFRE_RECUE = "offre_recue", "Offre recue"
        REPONSE_NEGATIVE = "reponse_negative", "Reponse negative"
        NOTE = "note", "Note libre"

    candidature = models.ForeignKey(Candidature, on_delete=models.CASCADE, related_name="actions")
    type_action = models.CharField(max_length=30, choices=TypeAction.choices)
    date_action = models.DateTimeField()
    commentaire = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
```

`date_action` est distincte de `date_creation` : l'utilisateur doit pouvoir
enregistrer un entretien passe la veille, pas seulement l'instant present.

Un changement de `type_action` vers `entretien_*`, `offre_recue` ou
`reponse_negative` peut proposer automatiquement (sans forcer) une mise a
jour du `statut` de la candidature parente, via une suggestion cote
frontend plutot qu'une regle backend rigide - l'utilisateur garde le
controle final du statut.

### 11.2 Endpoints associes

| Methode | Route | Description |
| --- | --- | --- |
| GET, POST | `/candidatures/{id}/actions/` | Liste ou ajout d'une action a l'historique |
| PUT, PATCH, DELETE | `/candidatures/{id}/actions/{action_id}/` | Modification ou suppression d'une action |

Implementation possible via une route imbriquee DRF ou un ViewSet separe
filtre par `candidature_id`, selon le pattern deja utilise pour les
sous-ressources existantes dans `views.py`.

### 11.3 Page de detail (`CandidatureDetail.jsx`)

Structure de haut en bas :

1. **En-tete** : titre du poste, entreprise, badges type de poste et statut
   (statut modifiable directement ici via un select), icone favori
   cliquable (bascule `favori`), lien "Voir l'annonce originale" (ouvre
   `url` dans un nouvel onglet), boutons "Modifier", "Archiver" et
   "Supprimer" distincts (voir remarque ci-dessous).
2. **Informations generales** : entreprise, lieu (si extrait ou renseigne),
   source du canal (`source_canal`, badge ou icone selon la plateforme),
   tags (chips editables inline), CV/lettre utilises (`cv_utilise`),
   date limite, date de relance, date d'ajout. Champs modifiables en ligne
   ou via le meme `CandidatureForm` reutilise en mode edition.
3. **Description complete** du poste (texte extrait ou saisi).
4. **Notes libres** (`notes` du modele) : zone de texte pour reflexions
   personnelles independantes de l'historique d'actions.
5. **Historique d'actions** : timeline verticale triee par `date_action`
   decroissante. Chaque entree affiche icone selon `type_action`, date,
   commentaire. Bouton "Ajouter une action" en haut de la timeline ouvrant
   un petit formulaire (`type_action`, `date_action`, `commentaire`).
6. **Archivage vs suppression** : "Archiver" (appel a
   `PATCH /candidatures/{id}/archiver/`) est l'action mise en avant pour une
   candidature refusee ou cloturee - elle sort de la liste active mais reste
   consultable via le filtre "Inclure les archivees". "Supprimer" reste
   disponible pour un vrai retrait definitif (ex. doublon cree par erreur),
   avec confirmation modale avant l'appel `DELETE`.

### 11.4 Composants frontend a creer

```text
frontend/src/pages/Candidatures.jsx           # page liste
frontend/src/pages/CandidatureDetail.jsx      # page detail
frontend/src/components/Candidatures/
    CandidatureCard.jsx
    CandidatureForm.jsx        # creation/edition, reutilise sur les deux pages
    CandidatureFiltres.jsx     # barre de filtres de la page liste
    ActionTimeline.jsx         # affichage de l'historique
    ActionForm.jsx             # ajout/edition d'une action
    TagsInput.jsx              # saisie/edition des tags, suggestion des tags existants
    CandidatureKanban.jsx      # vue kanban alternative a la liste (section 13)
```

Tous en MUI 7 avec l'API `size`, coherent avec la regle deja posee dans
`AGENTS.md` section 4.

## 12. Vue Kanban

Alternative a la liste sur la page `Candidatures.jsx`, activee par un
interrupteur "Liste / Kanban" en haut de page (etat garde en memoire locale
du composant, pas besoin de le persister cote backend pour ce lot).

- Une colonne par valeur de `Statut` (A postuler, Postule, Entretien,
  Refuse, Accepte).
- Chaque colonne affiche les `CandidatureCard` correspondantes, en version
  compacte (titre, entreprise, badges type/favori).
- Glisser-deposer une carte d'une colonne a l'autre declenche un
  `PATCH /candidatures/{id}/` mettant a jour `statut`.
- Les filtres de la section 10.3 s'appliquent aussi a la vue kanban (memes
  donnees filtrees, juste presentees differemment).

**Point d'attention technique** : ceci necessite une bibliotheque de
glisser-deposer (aucune n'est presente actuellement dans
`frontend/package.json`). Option courante et maintenue : `@hello-pangea/dnd`
(fork actif de `react-beautiful-dnd`). Ajout d'une nouvelle dependance
frontend - a confirmer explicitement avant implementation, cf. section 8.

## 13. Export CSV

Bouton "Exporter en CSV" sur la page liste, a cote de la barre de filtres.
Appelle `GET /candidatures/export_csv/` avec les filtres actifs en query
params, declenche le telechargement du fichier retourne (`Content-Disposition:
attachment`). Aucune dependance frontend supplementaire necessaire ; cote
backend, le module `csv` de la bibliotheque standard Python suffit, pas
besoin d'ajouter `pandas` pour un export aussi simple.

## 14. Champs complementaires a trancher

A confirmer avec l'utilisateur avant le lot 5-6, pour eviter une migration
supplementaire juste apres coup :

- `lieu` (ville/remote/hybride) : champ texte libre ou structure (ville +
  booleen teletravail) ?
- `salaire_estimation` : utile a beaucoup de plateformes d'offres, mais
  format libre (texte) suffit probablement pour ce lot plutot qu'un champ
  numerique avec devise.
- `contact` (nom/email de la personne recruteuse) : a inclure des ce lot ou
  reporte ?

Recommandation par defaut si pas de preference forte : ajouter `lieu` (texte
libre) et `teletravail` (choix : sur site / hybride / distanciel / non
precise) des ce lot, reporter `salaire_estimation` et `contact` a une
iteration ulterieure pour garder le premier lot raisonnable.
