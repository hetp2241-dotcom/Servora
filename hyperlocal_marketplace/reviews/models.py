from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count
from django.utils.translation import gettext_lazy as _


class Review(models.Model):
    booking = models.OneToOneField(
        'accounts.Booking',
        on_delete=models.CASCADE,
        related_name='marketplace_review',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marketplace_reviews_written',
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marketplace_reviews_received',
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['booking'], name='unique_review_per_booking'),
        ]
        indexes = [
            models.Index(fields=['provider', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"Review #{self.pk} for booking #{self.booking_id} ({self.rating}/5)"

    def clean(self):
        errors = {}
        booking = self.booking if self.booking_id else None

        if self.rating not in range(1, 6):
            errors['rating'] = _('Rating must be between 1 and 5.')

        if not self.comment or not self.comment.strip():
            errors['comment'] = _('Comment is required.')

        if booking:
            if booking.status != booking.Status.COMPLETED:
                errors['booking'] = _('Reviews can only be left for completed bookings.')
            if self.customer_id and booking.customer_id != self.customer_id:
                errors['customer'] = _('Customer must own the booking being reviewed.')
            if self.provider_id and booking.provider_id != self.provider_id:
                errors['provider'] = _('Provider must match the booking provider.')
            if self.customer_id and self.provider_id and self.customer_id == self.provider_id:
                errors['provider'] = _('Providers cannot review themselves.')

            duplicate = Review.objects.filter(booking=booking)
            if self.pk:
                duplicate = duplicate.exclude(pk=self.pk)
            if duplicate.exists():
                errors['booking'] = _('This booking already has a review.')
        else:
            errors['booking'] = _('A booking is required.')

        if self.customer_id and getattr(self.customer, 'role', None) != 'CUSTOMER':
            errors['customer'] = _('Only customers can create reviews.')

        if self.provider_id and getattr(self.provider, 'role', None) != 'PROVIDER':
            errors['provider'] = _('Reviews must target a provider account.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ProviderRatingStats(models.Model):
    provider = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rating_stats',
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    five_star_count = models.PositiveIntegerField(default=0)
    four_star_count = models.PositiveIntegerField(default=0)
    three_star_count = models.PositiveIntegerField(default=0)
    two_star_count = models.PositiveIntegerField(default=0)
    one_star_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'provider rating stats'

    def __str__(self):
        return f"{self.provider.full_name}: {self.average_rating}/5 ({self.review_count})"

    @property
    def distribution(self):
        return {
            5: self.five_star_count,
            4: self.four_star_count,
            3: self.three_star_count,
            2: self.two_star_count,
            1: self.one_star_count,
        }

    @classmethod
    def refresh_for_provider(cls, provider):
        reviews = Review.objects.filter(provider=provider)
        aggregate = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
        distribution = {
            rating: reviews.filter(rating=rating).count()
            for rating in range(1, 6)
        }
        stats, _ = cls.objects.update_or_create(
            provider=provider,
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
        return stats
