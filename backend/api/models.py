from django.conf import settings
from django.db import models


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
    class Status(models.TextChoices):
        CACHE_HIT = 'cache_hit', 'Cache hit'
        SUCCESS = 'success', 'Success'
        ERROR = 'error', 'Error'
        QUOTA_CACHE = 'quota_cache', 'Quota cache'
        QUOTA_FALLBACK = 'quota_fallback', 'Quota fallback'

    user_hash = models.CharField(max_length=64, db_index=True)
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

