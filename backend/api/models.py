from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class Candidature(models.Model):
    class TypePoste(models.TextChoices):
        STAGE = 'stage', 'Stage'
        ALTERNANCE = 'alternance', 'Alternance'
        CDI = 'cdi', 'CDI'
        CDD = 'cdd', 'CDD'
        FREELANCE = 'freelance', 'Freelance'
        AUTRE = 'autre', 'Autre'

    class Statut(models.TextChoices):
        A_POSTULER = 'a_postuler', 'A postuler'
        POSTULE = 'postule', 'Postule'
        ENTRETIEN = 'entretien', 'Entretien'
        REFUSE = 'refuse', 'Refuse'
        ACCEPTE = 'accepte', 'Accepte'

    class SourceCanal(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        INDEED = 'indeed', 'Indeed'
        WELCOME_JUNGLE = 'welcome_jungle', 'Welcome to the Jungle'
        SITE_DIRECT = 'site_direct', "Site de l'entreprise"
        COOPTATION = 'cooptation', 'Cooptation / reseau'
        AUTRE = 'autre', 'Autre'

    class ModeTravail(models.TextChoices):
        SUR_SITE = 'sur_site', 'Sur site'
        HYBRIDE = 'hybride', 'Hybride'
        TELETRAVAIL = 'teletravail', 'Teletravail'

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='candidatures',
    )
    url = models.URLField(max_length=1000)
    titre = models.CharField(max_length=255)
    entreprise = models.CharField(max_length=255, blank=True)
    lieu = models.CharField(max_length=255, blank=True)
    mode_travail = models.CharField(max_length=20, choices=ModeTravail.choices, blank=True)
    description = models.TextField(blank=True)
    type_poste = models.CharField(max_length=20, choices=TypePoste.choices, default=TypePoste.AUTRE)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.A_POSTULER)
    source_extraction = models.CharField(max_length=20, blank=True)
    source_canal = models.CharField(max_length=20, choices=SourceCanal.choices, default=SourceCanal.AUTRE)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    favori = models.BooleanField(default=False)
    archive = models.BooleanField(default=False)
    cv_utilise = models.CharField(max_length=255, blank=True)
    date_limite = models.DateField(null=True, blank=True)
    date_relance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['utilisateur', 'url'], name='unique_url_par_utilisateur'),
        ]

    def __str__(self):
        return f'{self.titre} - {self.entreprise}' if self.entreprise else self.titre


class ActionCandidature(models.Model):
    class TypeAction(models.TextChoices):
        CANDIDATURE_ENVOYEE = 'envoyee', 'Candidature envoyee'
        RELANCE = 'relance', 'Relance'
        ENTRETIEN_TEL = 'entretien_tel', 'Entretien telephonique'
        ENTRETIEN_VISIO = 'entretien_visio', 'Entretien visio'
        ENTRETIEN_PRESENTIEL = 'entretien_presentiel', 'Entretien presentiel'
        TEST_TECHNIQUE = 'test_technique', 'Test technique'
        OFFRE_RECUE = 'offre_recue', 'Offre recue'
        REPONSE_NEGATIVE = 'reponse_negative', 'Reponse negative'
        NOTE = 'note', 'Note libre'

    candidature = models.ForeignKey(
        Candidature,
        on_delete=models.CASCADE,
        related_name='actions',
    )
    type_action = models.CharField(max_length=30, choices=TypeAction.choices)
    date_action = models.DateTimeField()
    commentaire = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_action', '-id']

    def __str__(self):
        return f'{self.get_type_action_display()} - {self.candidature}'


class EntreeCacheRecommandation(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='entrees_cache_recommandation',
    )
    cle = models.CharField(max_length=255, unique=True)
    recommandation = models.JSONField()
    expire_a = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['utilisateur', 'expire_a']),
        ]


class JournalAppelLLM(models.Model):
    class Usage(models.TextChoices):
        RECOMMANDATION = 'recommandation', 'Recommandation'
        CANDIDATURE = 'candidature', 'Candidature'

    class Status(models.TextChoices):
        CACHE_HIT = 'cache_hit', 'Cache hit'
        SUCCESS = 'success', 'Success'
        ERROR = 'error', 'Error'
        QUOTA_CACHE = 'quota_cache', 'Quota cache'
        QUOTA_FALLBACK = 'quota_fallback', 'Quota fallback'

    user_hash = models.CharField(max_length=64, db_index=True)
    usage = models.CharField(max_length=20, choices=Usage.choices, default=Usage.RECOMMANDATION)
    prompt_hash = models.CharField(max_length=64, db_index=True)
    prompt_length = models.PositiveIntegerField()
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    cache_hit = models.BooleanField()
    error_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[
                    'cache_hit',
                    'success',
                    'error',
                    'quota_cache',
                    'quota_fallback',
                ]),
                name='api_journal_status_valid',
            ),
        ]
        indexes = [
            models.Index(fields=['user_hash', 'created_at']),
        ]

