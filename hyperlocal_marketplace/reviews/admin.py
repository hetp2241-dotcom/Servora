from django.contrib import admin
from django.core.exceptions import PermissionDenied

from .models import ProviderRatingStats, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'customer', 'provider', 'rating', 'created_at', 'updated_at')
    search_fields = (
        'comment',
        'customer__full_name',
        'customer__email',
        'provider__full_name',
        'provider__email',
        'booking__service__name',
    )
    list_filter = ('rating', 'created_at', 'updated_at')
    readonly_fields = ('booking', 'customer', 'provider', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        raise PermissionDenied('Direct admin deletion of reviews is disabled.')

    def delete_queryset(self, request, queryset):
        raise PermissionDenied('Bulk admin deletion of reviews is disabled.')


@admin.register(ProviderRatingStats)
class ProviderRatingStatsAdmin(admin.ModelAdmin):
    list_display = ('provider', 'average_rating', 'review_count', 'updated_at')
    readonly_fields = (
        'provider',
        'average_rating',
        'review_count',
        'five_star_count',
        'four_star_count',
        'three_star_count',
        'two_star_count',
        'one_star_count',
        'updated_at',
    )
    search_fields = ('provider__full_name', 'provider__email')
    ordering = ('-average_rating', '-review_count')

    def has_add_permission(self, request):
        return False
