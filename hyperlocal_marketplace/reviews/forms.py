from django import forms
from django.core.exceptions import ValidationError

from hyperlocal_marketplace.accounts.models import Booking

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        required=True,
        widget=forms.RadioSelect(
            choices=[(i, str(i)) for i in range(1, 6)],
            attrs={'class': 'star-rating-input'},
        ),
    )
    comment = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share what went well and what future customers should know.',
            }
        ),
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']

    def __init__(self, *args, user=None, booking=None, **kwargs):
        self.user = user
        self.booking = booking
        super().__init__(*args, **kwargs)
        if self.booking is not None:
            self.instance.booking = self.booking
            self.instance.provider = self.booking.provider
        if self.user is not None and self.user.is_authenticated:
            self.instance.customer = self.user

    def clean(self):
        cleaned_data = super().clean()
        booking = self.booking or getattr(self.instance, 'booking', None)

        if not self.user or not self.user.is_authenticated:
            raise ValidationError('You must be logged in to write a review.')
        if getattr(self.user, 'role', None) != 'CUSTOMER':
            raise ValidationError('Only customers can write reviews.')
        if not booking:
            raise ValidationError('A valid booking is required.')
        if booking.customer_id != self.user.id:
            raise ValidationError('You can only review your own bookings.')
        if booking.provider_id == self.user.id:
            raise ValidationError('Providers cannot review themselves.')
        if booking.status != Booking.Status.COMPLETED:
            raise ValidationError('Reviews are available after the booking is completed.')

        duplicate = Review.objects.filter(booking=booking)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError('This booking already has a review.')

        return cleaned_data

    def save(self, commit=True):
        review = super().save(commit=False)
        booking = self.booking or review.booking
        review.booking = booking
        review.customer = self.user
        review.provider = booking.provider
        if commit:
            review.save()
        return review
