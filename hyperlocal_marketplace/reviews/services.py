from django.db.models import Avg, Count

from hyperlocal_marketplace.accounts.models import User

from .models import ProviderRatingStats, Review


def average_rating(provider=None):
    queryset = Review.objects.all()
    if provider is not None:
        queryset = queryset.filter(provider=provider)
    return round(queryset.aggregate(value=Avg('rating'))['value'] or 0, 2)


def review_count(provider=None):
    queryset = Review.objects.all()
    if provider is not None:
        queryset = queryset.filter(provider=provider)
    return queryset.count()


def rating_distribution(provider=None):
    queryset = Review.objects.all()
    if provider is not None:
        queryset = queryset.filter(provider=provider)
    return {rating: queryset.filter(rating=rating).count() for rating in range(1, 6)}


def provider_statistics(provider):
    stats = ProviderRatingStats.objects.filter(provider=provider).first()
    if not stats:
        stats = ProviderRatingStats.refresh_for_provider(provider)
    latest_reviews = Review.objects.filter(provider=provider).select_related(
        'customer',
        'booking',
        'booking__service',
    )[:5]
    return {
        'average_rating': stats.average_rating,
        'review_count': stats.review_count,
        'distribution': stats.distribution,
        'latest_reviews': latest_reviews,
    }


def dashboard_statistics():
    providers = User.objects.filter(role=User.Role.PROVIDER).select_related('rating_stats')
    top_rated = providers.filter(rating_stats__review_count__gt=0).order_by(
        '-rating_stats__average_rating',
        '-rating_stats__review_count',
    )[:5]
    lowest_rated = providers.filter(rating_stats__review_count__gt=0).order_by(
        'rating_stats__average_rating',
        '-rating_stats__review_count',
    )[:5]
    return {
        'total_reviews': review_count(),
        'average_platform_rating': average_rating(),
        'distribution': rating_distribution(),
        'recent_reviews': Review.objects.select_related('customer', 'provider', 'booking__service')[:10],
        'top_rated_providers': top_rated,
        'lowest_rated_providers': lowest_rated,
    }


def refresh_provider_statistics(provider):
    return ProviderRatingStats.refresh_for_provider(provider)


def service_rating_queryset(queryset):
    return queryset.annotate(
        avg_rating=Avg('bookings__marketplace_review__rating'),
        review_count=Count('bookings__marketplace_review'),
    )
