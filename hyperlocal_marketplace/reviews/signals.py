from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import refresh_provider_statistics


@receiver(post_save, sender=Review)
def refresh_provider_stats_on_save(sender, instance, **kwargs):
    refresh_provider_statistics(instance.provider)


@receiver(post_delete, sender=Review)
def refresh_provider_stats_on_delete(sender, instance, **kwargs):
    refresh_provider_statistics(instance.provider)
