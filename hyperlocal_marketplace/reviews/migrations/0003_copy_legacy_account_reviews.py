from django.db import migrations
from django.db.models import Avg, Count


def copy_legacy_reviews(apps, schema_editor):
    LegacyReview = apps.get_model('accounts', 'Review')
    Review = apps.get_model('reviews', 'Review')
    ProviderRatingStats = apps.get_model('reviews', 'ProviderRatingStats')
    db_alias = schema_editor.connection.alias

    provider_ids = set()
    for legacy in LegacyReview.objects.using(db_alias).select_related('booking', 'customer', 'provider'):
        Review.objects.using(db_alias).get_or_create(
            booking_id=legacy.booking_id,
            defaults={
                'customer_id': legacy.customer_id,
                'provider_id': legacy.provider_id,
                'rating': legacy.rating,
                'comment': legacy.comment,
                'created_at': legacy.created_at,
                'updated_at': legacy.created_at,
            },
        )
        provider_ids.add(legacy.provider_id)

    for provider_id in provider_ids:
        reviews = Review.objects.using(db_alias).filter(provider_id=provider_id)
        aggregate = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
        distribution = {rating: reviews.filter(rating=rating).count() for rating in range(1, 6)}
        ProviderRatingStats.objects.using(db_alias).update_or_create(
            provider_id=provider_id,
            defaults={
                'average_rating': round(aggregate['avg'] or 0, 2),
                'review_count': aggregate['count'] or 0,
                'five_star_count': distribution[5],
                'four_star_count': distribution[4],
                'three_star_count': distribution[3],
                'two_star_count': distribution[2],
                'one_star_count': distribution[1],
            },
        )


def reverse_copy_legacy_reviews(apps, schema_editor):
    Review = apps.get_model('reviews', 'Review')
    ProviderRatingStats = apps.get_model('reviews', 'ProviderRatingStats')
    db_alias = schema_editor.connection.alias
    Review.objects.using(db_alias).all().delete()
    ProviderRatingStats.objects.using(db_alias).all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0002_rename_reviews_rev_provide_75377a_idx_reviews_rev_provide_688176_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(copy_legacy_reviews, reverse_copy_legacy_reviews),
    ]
