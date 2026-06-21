from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from hyperlocal_marketplace.accounts.models import Booking, User

from .forms import ReviewForm
from .models import Review
from .services import dashboard_statistics, provider_statistics, rating_distribution


class CustomerRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != User.Role.CUSTOMER:
            messages.error(request, 'Only customers can manage reviews.')
            return redirect('dashboard_redirect')
        return super().dispatch(request, *args, **kwargs)


class ReviewOwnerMixin(LoginRequiredMixin):
    def get_queryset(self):
        return Review.objects.select_related('booking', 'booking__service', 'customer', 'provider').filter(
            customer=self.request.user
        )


class CreateReviewView(CustomerRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(
            Booking.objects.select_related('service', 'customer', 'provider'),
            pk=kwargs['booking_id'],
        )
        if self.booking.customer_id != request.user.id:
            raise PermissionDenied('You can only review your own bookings.')
        if self.booking.provider_id == request.user.id:
            raise PermissionDenied('Providers cannot review themselves.')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['booking'] = self.booking
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Thanks for sharing your review.')
        response = super().form_valid(form)

        # NEW_REVIEW notification (provider receives)
        booking = self.booking
        provider = booking.provider
        review = self.object

        from hyperlocal_marketplace.accounts.notifications import create_notification_and_dispatch

        create_notification_and_dispatch(
            recipient=provider,
            actor=self.request.user,
            type='NEW_REVIEW',
            title='New review',
            message=f"You received a new review for booking #{booking.id}.",
            link=f"/provider-dashboard/#reviews",
            idempotency_key=f"NEW_REVIEW:{review.id}",
        )

        return response


    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the review form errors.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.booking
        context['is_update'] = False
        return context

    def get_success_url(self):
        return reverse('customer_dashboard') + '#reviews'


class UpdateReviewView(CustomerRequiredMixin, ReviewOwnerMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'reviews/review_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['booking'] = self.object.booking
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Review updated successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.object.booking
        context['is_update'] = True
        return context

    def get_success_url(self):
        return reverse('customer_dashboard') + '#reviews'


class DeleteReviewView(CustomerRequiredMixin, ReviewOwnerMixin, DeleteView):
    model = Review
    template_name = 'reviews/review_form.html'
    success_url = reverse_lazy('customer_dashboard')

    def post(self, request, *args, **kwargs):
        messages.success(request, 'Review deleted successfully.')
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('customer_dashboard') + '#reviews'


class ReviewListView(LoginRequiredMixin, ListView):
    model = Review
    template_name = 'reviews/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 10

    def get_queryset(self):
        queryset = Review.objects.select_related('booking', 'booking__service', 'customer', 'provider')
        user = self.request.user
        if user.role == User.Role.CUSTOMER:
            queryset = queryset.filter(customer=user)
        elif user.role == User.Role.PROVIDER:
            queryset = queryset.filter(provider=user)

        rating = self.request.GET.get('rating')
        if rating in ['1', '2', '3', '4', '5']:
            queryset = queryset.filter(rating=int(rating))

        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(
                Q(comment__icontains=search) |
                Q(booking__service__name__icontains=search) |
                Q(customer__full_name__icontains=search) |
                Q(provider__full_name__icontains=search)
            )

        sort = self.request.GET.get('sort', 'newest')
        ordering = {
            'oldest': 'created_at',
            'rating_high': '-rating',
            'rating_low': 'rating',
            'newest': '-created_at',
        }.get(sort, '-created_at')
        return queryset.order_by(ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_rating'] = self.request.GET.get('rating', '')
        context['selected_sort'] = self.request.GET.get('sort', 'newest')
        context['search_query'] = self.request.GET.get('q', '')
        context['summary'] = dashboard_statistics() if self.request.user.role == User.Role.ADMIN else None
        return context


class ProviderRatingSummaryView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'reviews/rating_summary.html'
    context_object_name = 'provider'

    def get_queryset(self):
        queryset = User.objects.filter(role=User.Role.PROVIDER)
        if self.request.user.role == User.Role.PROVIDER:
            queryset = queryset.filter(pk=self.request.user.pk)
        return queryset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        stats = provider_statistics(self.object)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({
                'provider_id': self.object.id,
                'average_rating': float(stats['average_rating']),
                'review_count': stats['review_count'],
                'distribution': stats['distribution'],
            })
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = provider_statistics(self.object)
        context['distribution'] = rating_distribution(self.object)
        context['distribution_counts'] = [context['distribution'].get(rating, 0) for rating in range(1, 6)]
        return context
