# Fonctionnalité : Gestion et envoi de candidatures spontanées par email

## 1. Contexte du projet

Le projet "Mon Agenda Numérique" est une application web composée notamment de :

- Backend : Django / Django REST Framework
- Frontend : React
- Base de données : PostgreSQL
- Module existant de gestion des candidatures
- Historique des actions
- Vue détail d'une candidature
- Import d'offres depuis une URL
- Kanban
- Export CSV
- Assistant IA avec mécanisme de confirmation pour les actions d'écriture

Je souhaite ajouter une nouvelle fonctionnalité permettant de préparer, gérer et envoyer des candidatures spontanées directement depuis l'application.

Cette fonctionnalité doit être intégrée au module Candidatures existant et ne doit pas être développée comme une application séparée.


# 2. Objectif général

L'objectif est de pouvoir :

1. enregistrer une entreprise et éventuellement un contact ;
2. enregistrer l'adresse email du destinataire ;
3. préparer automatiquement un email de candidature spontanée ;
4. joindre automatiquement mon CV ;
5. prévisualiser et modifier l'email avant l'envoi ;
6. confirmer explicitement l'envoi ;
7. envoyer l'email depuis mon compte Gmail ;
8. enregistrer le résultat dans la base de données ;
9. retrouver l'email envoyé dans l'historique de la candidature ;
10. préparer plusieurs candidatures sans envoyer immédiatement les emails.

Le système ne doit jamais envoyer un email automatiquement sans confirmation explicite de l'utilisateur.


# 3. Parcours utilisateur principal

Exemple :

Je trouve une entreprise intéressante.

Je crée ou complète une candidature :

Entreprise :
Doctolib

Type :
Candidature spontanée

Poste recherché :
Développeur Full Stack / Backend

Contact :
Sophie Martin

Email :
sophie.martin@example.com

Je clique ensuite sur :

"Préparer un email"

L'application génère un brouillon.


# 4. Génération du brouillon

Pour la V1, aucun LLM n'est nécessaire.

Le système utilise un template.

Exemple d'objet :

Candidature spontanée – Alternance Développeur Full Stack

Exemple de contenu :

Bonjour Madame Martin,

Je me permets de vous contacter dans le cadre de ma recherche
d'une alternance en développement web/full-stack.

Actuellement étudiant en Licence Professionnelle Projet Web et
Mobile à Sorbonne Université, je souhaiterais vous proposer ma
candidature au sein de Doctolib.

Vous trouverez mon CV en pièce jointe.

Je reste à votre disposition pour tout échange.

Cordialement,

Leiwei SHI

Portfolio : [URL]
GitHub : [URL]


# 5. Variables du template

Le système doit pouvoir remplacer automatiquement certaines variables :

{{ entreprise }}
{{ nom_contact }}
{{ prenom_contact }}
{{ civilite }}
{{ poste }}
{{ formation }}
{{ portfolio_url }}
{{ github_url }}

Par exemple :

{{ entreprise }} -> Doctolib
{{ nom_contact }} -> Martin
{{ civilite }} -> Madame

Si le nom ou la civilité du contact n'est pas disponible, utiliser une formule générique appropriée :

Bonjour Madame, Monsieur,


# 6. Prévisualisation

La génération d'un email ne doit PAS déclencher son envoi.

Après génération, afficher une interface permettant de vérifier :

DESTINATAIRE
sophie.martin@example.com

OBJET
Candidature spontanée – Alternance Développeur Full Stack

MESSAGE
[éditeur permettant de modifier le texte]

PIÈCES JOINTES
CV_Leiwei_SHI.pdf

Actions :

[Enregistrer le brouillon]
[Annuler]
[Envoyer]

L'utilisateur doit pouvoir modifier :

- le destinataire ;
- l'objet ;
- le contenu.

L'utilisateur doit voir clairement les pièces jointes avant l'envoi.


# 7. Gestion du CV

Créer un système permettant de définir un CV par défaut.

Par exemple dans le profil ou les paramètres :

CV par défaut

CV_Leiwei_SHI.pdf

[Remplacer]

Pour la V1, un seul CV par défaut suffit.

Lors de la préparation d'un email de candidature, le CV est automatiquement proposé comme pièce jointe.

Ne pas envoyer le CV tant que l'utilisateur n'a pas confirmé l'email.

Prévoir une architecture permettant éventuellement d'avoir plusieurs CV plus tard :

- CV Full Stack
- CV Backend
- CV Frontend

Mais ne pas implémenter cette fonctionnalité en V1 si elle complexifie inutilement le système.


# 8. Lettre de motivation

La V1 ne doit pas générer automatiquement de lettre de motivation PDF.

Une candidature spontanée standard sera constituée de :

EMAIL PERSONNALISÉ
+
CV

Le contenu de l'email sert donc de message de candidature.

Une gestion des lettres de motivation pourra être ajoutée ultérieurement.


# 9. Gmail

L'envoi doit être effectué depuis mon propre compte Gmail.

Solution privilégiée :

Gmail API + OAuth 2.0.

Ne jamais stocker le mot de passe principal du compte Google dans le code, Git, PostgreSQL ou le frontend.

Prévoir une fonction du type :

"Connecter mon compte Gmail"

Après autorisation, le backend doit pouvoir utiliser les autorisations nécessaires pour envoyer les emails.

Les secrets et credentials nécessaires doivent être stockés de manière sécurisée et ne doivent jamais être commit dans Git.


# 10. Architecture

Architecture souhaitée :

React
    |
    | REST API
    v
Django REST Framework
    |
    +---- Candidature
    |
    +---- EmailCandidature
    |
    +---- EmailTemplate / service de template
    |
    +---- CV
    |
    +---- GmailService
    |
    +---- Historique
    |
    v
PostgreSQL

Pour l'envoi :

React
  |
  | confirmation utilisateur
  v
Django
  |
  | validation serveur
  v
GmailService
  |
  | Gmail API
  v
Gmail


# 11. Modèle de données

Analyser les modèles existants avant de créer de nouveaux champs ou modèles.

Éviter de dupliquer des informations déjà présentes dans Candidature.

Il devrait néanmoins exister une entité représentant un email.

Exemple conceptuel :

EmailCandidature

- id
- candidature
- recipient_email
- recipient_name
- subject
- body
- status
- created_at
- updated_at
- sent_at
- error_message
- gmail_message_id éventuellement


# 12. Statuts d'un email

Prévoir des statuts explicites, par exemple :

DRAFT
READY
SENDING
SENT
FAILED
CANCELLED

Le choix exact doit être adapté à l'architecture existante.


# 13. Historique

Chaque envoi doit être traçable.

Exemple :

22/09/2026 18:30
Email de candidature préparé

22/09/2026 18:34
Email modifié

22/09/2026 18:36
Email envoyé à recrutement@example.com

Le détail d'une candidature doit permettre de retrouver les emails associés.


# 14. Plusieurs emails pour une même candidature

Ne pas limiter une candidature à un seul email.

Relation souhaitée :

Candidature
    |
    +-- Email candidature initiale
    |
    +-- Relance 1
    |
    +-- Relance 2

Une candidature doit donc pouvoir posséder plusieurs EmailCandidature.


# 15. Préparation de plusieurs candidatures

L'utilisateur doit pouvoir sélectionner plusieurs candidatures.

Exemple :

[x] Entreprise A
[x] Entreprise B
[x] Entreprise C
[ ] Entreprise D

Bouton :

"Préparer les emails"

Le système crée alors plusieurs brouillons indépendants.

Il ne doit PAS envoyer immédiatement les emails.


# 16. Interface de préparation en masse

Exemple :

3 emails préparés

Entreprise A
destinataire : xxx@example.com
[Brouillon] [Voir]

Entreprise B
destinataire : xxx@example.com
[Brouillon] [Voir]

Entreprise C
destinataire : xxx@example.com
[Brouillon] [Voir]

Chaque email doit rester indépendant.

Ne jamais mettre plusieurs entreprises dans CC ou BCC.


# 17. Envoi V1

Pour la première version, privilégier l'envoi individuel.

Exemple :

Entreprise A
[Voir] [Envoyer]

Entreprise B
[Voir] [Envoyer]

Entreprise C
[Voir] [Envoyer]

L'utilisateur vérifie puis confirme chaque envoi.

Une fonctionnalité "Envoyer tous les emails validés" pourra être étudiée ensuite.


# 18. Confirmation obligatoire

La préparation d'un brouillon et l'envoi doivent être deux actions différentes.

PREPARE
    ↓
DRAFT
    ↓
REVIEW
    ↓
CONFIRM
    ↓
SEND

Le backend ne doit pas considérer une simple génération de brouillon comme une autorisation d'envoi.

L'envoi doit toujours provenir d'une action explicite de l'utilisateur.


# 19. Validation côté serveur

Avant chaque envoi, le backend doit vérifier au minimum :

- candidature appartenant à l'utilisateur connecté ;
- email valide ;
- brouillon existant ;
- CV accessible ;
- compte Gmail connecté ;
- email pas déjà en cours d'envoi ;
- email pas déjà envoyé accidentellement deux fois.

Ne pas faire confiance uniquement aux contrôles React.


# 20. Protection contre le double envoi

Un double clic ou une requête répétée ne doit pas envoyer deux emails identiques.

Prévoir une protection contre :

- double clic ;
- retry HTTP ;
- rafraîchissement ;
- requête envoyée deux fois.

L'opération d'envoi doit autant que possible être idempotente.


# 21. Gestion des erreurs

Si Gmail renvoie une erreur :

- ne pas marquer l'email comme SENT ;
- enregistrer FAILED ;
- enregistrer une erreur exploitable sans stocker inutilement des données sensibles ;
- afficher une information claire à l'utilisateur.

Exemple :

Échec de l'envoi.

Votre brouillon a été conservé.

[Réessayer]


# 22. Sécurité

Ne jamais exposer au frontend :

- secret OAuth ;
- credentials Gmail ;
- token sensible ;
- SECRET_KEY Django.

Ne jamais les inclure dans Git.

Utiliser les variables d'environnement et les mécanismes sécurisés adaptés à OAuth.

Limiter les permissions Gmail au strict nécessaire.


# 23. Tests backend

Ajouter des tests pour au minimum :

- génération du brouillon ;
- remplacement des variables ;
- fallback "Bonjour Madame, Monsieur" ;
- utilisateur ne pouvant pas accéder aux emails d'un autre utilisateur ;
- validation email ;
- CV absent ;
- Gmail non connecté ;
- envoi réussi ;
- échec Gmail ;
- protection contre double envoi ;
- historique créé après envoi ;
- aucune requête Gmail lors de la simple préparation d'un brouillon.


# 24. Tests frontend

Tester au minimum :

- bouton "Préparer un email" ;
- formulaire de prévisualisation ;
- modification de l'objet ;
- modification du contenu ;
- affichage du CV ;
- confirmation ;
- annulation ;
- état loading pendant l'envoi ;
- succès ;
- erreur ;
- prévention du double clic.


# 25. Ce qui n'est PAS inclus dans la V1

Ne pas implémenter pour le moment :

- scraping automatique massif d'emails ;
- récupération automatique de centaines d'entreprises ;
- génération automatique d'adresses email ;
- scraping LinkedIn ;
- envoi automatique sans confirmation ;
- campagnes de centaines d'emails ;
- LLM pour rédiger les emails ;
- génération automatique de lettre de motivation ;
- relances automatiques ;
- planification automatique ;
- tracking d'ouverture ;
- tracking de clic ;
- système marketing/newsletter.

La V1 doit rester un outil personnel de gestion de candidatures.


# 26. Évolution V2

Après validation de la V1, envisager :

- génération LLM d'un paragraphe personnalisé ;
- plusieurs templates ;
- plusieurs CV ;
- lettre de motivation ;
- préparation des relances ;
- rappel après X jours sans réponse ;
- suggestions de contacts publics ;
- traitement par lots avec limites raisonnables.


# 27. Évolution LLM

Le LLM pourra éventuellement recevoir :

- entreprise ;
- poste ;
- description de l'offre ;
- informations publiques pertinentes ;
- profil du candidat.

Il pourra proposer un email personnalisé.

Mais :

LLM -> PROPOSE

et jamais :

LLM -> SEND

L'utilisateur doit toujours garder le contrôle de l'envoi.


# 28. Intégration avec le système existant

Réutiliser autant que possible :

- modèle Candidature existant ;
- historique existant ;
- authentification existante ;
- permissions existantes ;
- frontend existant ;
- système de confirmation existant si pertinent.

Ne pas créer une deuxième architecture parallèle si les composants existants peuvent être réutilisés.


# 29. Résultat final attendu de la V1

Depuis Mon Agenda Numérique, je dois pouvoir :

1. ouvrir une candidature ;
2. ajouter l'email d'un contact ;
3. cliquer sur "Préparer un email" ;
4. obtenir automatiquement un brouillon ;
5. voir le destinataire ;
6. voir et modifier l'objet ;
7. voir et modifier le message ;
8. voir le CV qui sera joint ;
9. confirmer explicitement ;
10. envoyer depuis mon Gmail ;
11. voir si l'envoi a réussi ;
12. retrouver l'envoi dans l'historique de la candidature.


# 30. Travail demandé à Codex

Avant toute modification du code :

1. inspecter l'architecture actuelle du repository ;
2. identifier les modèles, serializers, views, services, composants React et tests existants concernés ;
3. vérifier ce qui existe déjà dans Candidature et Historique ;
4. identifier ce qui peut être réutilisé ;
5. proposer l'architecture précise adaptée au projet réel ;
6. proposer les migrations nécessaires ;
7. proposer les endpoints API ;
8. proposer les composants/pages frontend ;
9. proposer la stratégie Gmail OAuth ;
10. proposer les tests ;
11. découper l'implémentation en lots progressifs.

Ne pas modifier le code dans un premier temps.

Présenter d'abord un plan d'implémentation détaillé basé sur le code réellement présent dans le repository.

Éviter les refactorings non nécessaires et conserver la compatibilité avec les fonctionnalités existantes.
