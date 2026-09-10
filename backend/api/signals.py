"""Invalidation du cache de recommandations apres les changements utilisateur."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from agenda.models import PreferenceUtilisateur, Tache
from api.llm_performance import invalider_cache_utilisateur


@receiver(post_save, sender=Tache, dispatch_uid='api.invalidate_task_cache_after_save')
def invalider_cache_apres_sauvegarde_tache(sender, instance, **kwargs):
    invalider_cache_utilisateur(instance.utilisateur_id)


@receiver(post_delete, sender=Tache, dispatch_uid='api.invalidate_task_cache_after_delete')
def invalider_cache_apres_suppression_tache(sender, instance, **kwargs):
    invalider_cache_utilisateur(instance.utilisateur_id)


@receiver(post_save, sender=PreferenceUtilisateur, dispatch_uid='api.invalidate_preference_cache_after_save')
def invalider_cache_apres_sauvegarde_preference(sender, instance, **kwargs):
    invalider_cache_utilisateur(instance.utilisateur_id)


@receiver(post_delete, sender=PreferenceUtilisateur, dispatch_uid='api.invalidate_preference_cache_after_delete')
def invalider_cache_apres_suppression_preference(sender, instance, **kwargs):
    invalider_cache_utilisateur(instance.utilisateur_id)
