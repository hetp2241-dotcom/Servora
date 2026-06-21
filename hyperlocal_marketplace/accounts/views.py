from decimal import Decimal, InvalidOperation
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
from .forms import (
    CustomUserCreationForm,
    CustomLoginForm,
    ProviderProfileForm,
    ServiceForm,
    BookingForm,
    ServiceFilterForm,
)
from .models import (
    User,
    Category,
    ProviderProfile,
    Service,
    Booking,
    Payment,
    ChatMessage,
)
from .decorators import role_required
from .stripe_config import create_checkout_session, get_stripe_module
from hyperlocal_marketplace.reviews.models import Review
from hyperlocal_marketplace.reviews.services import (
    dashboard_statistics as review_dashboard_statistics,
    provider_statistics,
    service_rating_queryset,
)

logger = logging.getLogger(__name__)


def _mark_payment_paid(payment, stripe_payment_id=''):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related('booking').get(pk=payment.pk)
        booking = payment.booking
        payment.payment_status = Payment.Status.PAID
        if stripe_payment_id and not payment.stripe_payment_id:
            payment.stripe_payment_id = stripe_payment_id
        payment.save(update_fields=['payment_status', 'stripe_payment_id'])
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=['status'])
    logger.info('Payment marked paid for booking_id=%s payment_id=%s', booking.id, payment.id)
    return payment


def _mark_payment_failed(payment):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        payment.payment_status = Payment.Status.FAILED
        payment.save(update_fields=['payment_status'])
    logger.warning('Payment marked failed for booking_id=%s payment_id=%s', payment.booking_id, payment.id)
    return payment


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account created successfully for {user.full_name}! You can now login.")
            return redirect('login')
        messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    next_url = request.GET.get('next', 'dashboard_redirect')
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            remember_me = form.cleaned_data.get('remember_me')
            if remember_me:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)
            messages.success(request, f"Welcome back, {user.full_name}!")
            if next_url and next_url != 'dashboard_redirect':
                return redirect(next_url)
            return redirect('dashboard_redirect')
        messages.error(request, 'Invalid email or password.')
    else:
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_redirect_view(request):
    if request.user.role == User.Role.ADMIN:
        return redirect('admin_dashboard')
    if request.user.role == User.Role.PROVIDER:
        return redirect('provider_dashboard')
    return redirect('customer_dashboard')


class ServiceListView(ListView):
    model = Service
    template_name = 'accounts/service_list.html'
    context_object_name = 'services'
    paginate_by = 12

    def get_queryset(self):
        queryset = service_rating_queryset(
            Service.objects.select_related('provider', 'category', 'provider__provider_profile')
        )
        search = self.request.GET.get('search', '').strip()
        category_name = self.request.GET.get('category', '').strip()
        city = self.request.GET.get('city', '').strip()
        min_price = self.request.GET.get('min_price', '').strip()
        max_price = self.request.GET.get('max_price', '').strip()
        experience = self.request.GET.get('experience', '').strip()
        verified_only = self.request.GET.get('verified_only')
        available_only = self.request.GET.get('available_only')
        sort_by = self.request.GET.get('sort_by', 'newest_first')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(provider__full_name__icontains=search) |
                Q(category__name__icontains=search)
            )

        if category_name:
            queryset = queryset.filter(category__name__iexact=category_name)

        if city:
            queryset = queryset.filter(provider__provider_profile__city__iexact=city)

        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except (InvalidOperation, ValueError):
                pass

        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except (InvalidOperation, ValueError):
                pass

        if experience:
            try:
                queryset = queryset.filter(provider__provider_profile__experience_years__gte=int(experience))
            except ValueError:
                pass

        if verified_only and verified_only.lower() in ['true', '1', 'yes', 'on']:
            queryset = queryset.filter(provider__provider_profile__is_verified=True)

        if available_only and available_only.lower() in ['true', '1', 'yes', 'on']:
            queryset = queryset.filter(is_available=True)
        else:
            queryset = queryset.filter(is_available=True)

        ordering_map = {
            'newest_first': '-created_at',
            'oldest_first': 'created_at',
            'price_low': 'price',
            'price_high': '-price',
            'experience_high': '-provider__provider_profile__experience_years',
            'provider_name': 'provider__full_name',
        }
        queryset = queryset.order_by(ordering_map.get(sort_by, '-created_at'))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_form = ServiceFilterForm(self.request.GET or None)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)

        active_filters = []
        if self.request.GET.get('search'):
            params = query_params.copy()
            params.pop('search', None)
            active_filters.append({'label': self.request.GET.get('search'), 'url': f'?{params.urlencode()}'.rstrip('?')})
        if self.request.GET.get('category'):
            params = query_params.copy()
            params.pop('category', None)
            active_filters.append({'label': self.request.GET.get('category'), 'url': f'?{params.urlencode()}'.rstrip('?')})
        if self.request.GET.get('city'):
            params = query_params.copy()
            params.pop('city', None)
            active_filters.append({'label': self.request.GET.get('city'), 'url': f'?{params.urlencode()}'.rstrip('?')})
        if self.request.GET.get('min_price') or self.request.GET.get('max_price'):
            min_price = self.request.GET.get('min_price', '').strip()
            max_price = self.request.GET.get('max_price', '').strip()
            label = 'Price '
            if min_price and max_price:
                label += f'₹{min_price} - ₹{max_price}'
            elif min_price:
                label += f'₹{min_price}+'
            elif max_price:
                label += f'Up to ₹{max_price}'
            params = query_params.copy()
            params.pop('min_price', None)
            params.pop('max_price', None)
            active_filters.append({'label': label, 'url': f'?{params.urlencode()}'.rstrip('?')})
        if self.request.GET.get('experience'):
            experience_choice = filter_form.fields['experience'].choices
            experience_label = dict(experience_choice).get(self.request.GET.get('experience'), 'Experience')
            params = query_params.copy()
            params.pop('experience', None)
            active_filters.append({'label': experience_label, 'url': f'?{params.urlencode()}'.rstrip('?')})
        if self.request.GET.get('verified_only') in ['true', '1', 'yes', 'on']:
            params = query_params.copy()
            params.pop('verified_only', None)
            active_filters.append({'label': 'Verified providers only', 'url': f'?{params.urlencode()}'.rstrip('?')})
        if self.request.GET.get('available_only') in ['true', '1', 'yes', 'on']:
            params = query_params.copy()
            params.pop('available_only', None)
            active_filters.append({'label': 'Available services only', 'url': f'?{params.urlencode()}'.rstrip('?')})

        context['filter_form'] = filter_form
        context['categories'] = Category.objects.all()
        context['querystring'] = query_params.urlencode()
        context['active_filters'] = active_filters
        return context


class ServiceDetailView(DetailView):
    model = Service
    template_name = 'accounts/service_detail.html'
    context_object_name = 'service'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking_form'] = BookingForm()
        context['provider_profile'] = getattr(self.object.provider, 'provider_profile', None)
        context['now'] = timezone.now()
        reviews = Review.objects.filter(booking__service=self.object).select_related('customer', 'provider').order_by('-created_at')
        context['reviews'] = reviews
        context['average_rating'] = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        context['total_reviews'] = reviews.count()
        if self.object.provider_id:
            context['provider_rating_stats'] = provider_statistics(self.object.provider)
        context['related_services'] = self.object.provider.services.filter(is_available=True).exclude(pk=self.object.pk)[:4]
        return context


class ProviderProfileListView(ListView):
    model = ProviderProfile
    template_name = 'accounts/provider_profile_list.html'
    context_object_name = 'profiles'
    paginate_by = 12

    def get_queryset(self):
        return ProviderProfile.objects.select_related('user').order_by('-is_verified', 'full_name')


class ProviderProfileDetailView(DetailView):
    model = ProviderProfile
    template_name = 'accounts/provider_profile_detail.html'
    context_object_name = 'profile'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = self.object.user.services.filter(is_available=True).select_related('category')
        context['rating_stats'] = provider_statistics(self.object.user)
        return context


@login_required
@role_required('PROVIDER')
def provider_profile_edit(request):
    profile = get_object_or_404(ProviderProfile, user=request.user)

    if request.method == 'POST':
        form = ProviderProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Provider profile updated successfully.')
            return redirect('provider_dashboard')
        messages.error(request, 'Please correct the errors in your provider profile form.')
    else:
        form = ProviderProfileForm(instance=profile)

    return render(request, 'accounts/provider_profile_form.html', {'form': form})


@login_required
@role_required('CUSTOMER')
def customer_dashboard(request):
    services = Service.objects.filter(is_available=True).select_related('provider', 'category')[:8]

    providers = (
        User.objects.filter(role=User.Role.PROVIDER)
        .select_related('provider_profile')
        .exclude(provider_profile__latitude__isnull=True)
        .exclude(provider_profile__longitude__isnull=True)
    )

    status_filter = request.GET.get('status', 'all').upper()
    bookings = Booking.objects.filter(customer=request.user).select_related('service', 'provider').prefetch_related('payments').annotate(
        has_review=Exists(Review.objects.filter(booking_id=OuterRef('pk')))
    )

    if status_filter in Booking.Status.values:
        bookings = bookings.filter(status=status_filter)
    bookings = bookings.order_by('-created_at')
    payment_history = Payment.objects.filter(booking__customer=request.user).select_related(
        'booking',
        'booking__service',
        'booking__provider',
    ).order_by('-created_at')
    my_reviews = Review.objects.filter(customer=request.user).select_related('booking', 'booking__service', 'provider').order_by('-created_at')

    selected_status = status_filter if status_filter in Booking.Status.values else 'all'

    chat_partner_id = request.GET.get('chat_with')
    chat_partner = None
    chat_messages = []
    if chat_partner_id:
        chat_partner = User.objects.filter(id=chat_partner_id, role=User.Role.PROVIDER).first()
        if chat_partner:
            chat_messages = ChatMessage.objects.filter(
                Q(sender=request.user, receiver=chat_partner) |
                Q(sender=chat_partner, receiver=request.user)
            ).order_by('timestamp')

    # Build provider list for the customer “Nearby Service Providers” map.
    # We also include a service category (if the provider has services), otherwise fallback to empty.
    providers_json = []
    for p in providers:
        provider_profile = getattr(p, 'provider_profile', None)
        if not provider_profile:
            continue
        first_service = p.services.select_related('category').filter(is_available=True).first()
        providers_json.append({
            'latitude': float(provider_profile.latitude),
            'longitude': float(provider_profile.longitude),
            'provider_name': p.full_name,
            'service_category': (first_service.category.name if first_service and first_service.category else ''),
            'address': provider_profile.address or '',
        })

    # Serialize to strict JSON so the template can safely embed it into a data-* attribute
    # and the client-side code can do JSON.parse(...) successfully.
    import json
    nearby_providers_json = json.dumps(providers_json)



    context = {
        'services': services,
        'bookings': bookings,
        'providers': providers,
        'nearby_providers_json': nearby_providers_json,


        'chat_partner': chat_partner,
        'chat_messages': chat_messages,
        'selected_status': selected_status,
        'payment_history': payment_history,
        'my_reviews': my_reviews,
    }
    return render(request, 'accounts/customer_dashboard.html', context)


@login_required
@role_required('PROVIDER')
def provider_dashboard(request):
    profile = get_object_or_404(ProviderProfile, user=request.user)
    services = Service.objects.filter(provider=request.user).select_related('category').order_by('-created_at')
    status_filter = request.GET.get('status', 'all').upper()
    bookings = Booking.objects.filter(provider=request.user).select_related('service', 'customer')
    if status_filter in Booking.Status.values:
        bookings = bookings.filter(status=status_filter)
    bookings = bookings.order_by('-created_at')
    service_form = ServiceForm()
    categories = Category.objects.all()
    selected_status = status_filter if status_filter in Booking.Status.values else 'all'

    total_services = services.count()
    active_services = services.filter(is_available=True).count()
    recent_services = services[:4]
    profile_completion = profile.completion_percentage
    review_stats = provider_statistics(request.user)

    customer_ids = bookings.values_list('customer_id', flat=True).distinct()
    customers = User.objects.filter(role=User.Role.CUSTOMER, id__in=customer_ids)
    if not customers.exists():
        customers = User.objects.filter(role=User.Role.CUSTOMER)

    chat_partner_id = request.GET.get('chat_with')
    chat_partner = None
    chat_messages = []
    if chat_partner_id:
        chat_partner = User.objects.filter(id=chat_partner_id, role=User.Role.CUSTOMER).first()
        if chat_partner:
            chat_messages = ChatMessage.objects.filter(
                Q(sender=request.user, receiver=chat_partner) |
                Q(sender=chat_partner, receiver=request.user)
            ).order_by('timestamp')

    context = {
        'profile': profile,
        'services': services,
        'bookings': bookings,
        'service_form': service_form,
        'categories': categories,
        'total_services': total_services,
        'active_services': active_services,
        'recent_services': recent_services,
        'profile_completion': profile_completion,
        'customers': customers,
        'chat_partner': chat_partner,
        'chat_messages': chat_messages,
        'selected_status': selected_status,
        'review_stats': review_stats,
    }
    return render(request, 'accounts/provider_dashboard.html', context)


@login_required
@role_required('ADMIN')
def admin_dashboard(request):
    users = User.objects.all().order_by('-date_joined')
    providers = User.objects.filter(role=User.Role.PROVIDER)
    status_filter = request.GET.get('status', 'all').upper()
    search_query = request.GET.get('search', '').strip()
    bookings = Booking.objects.all().select_related('customer', 'provider', 'service')
    if status_filter in Booking.Status.values:
        bookings = bookings.filter(status=status_filter)
    if search_query:
        bookings = bookings.filter(
            Q(customer__full_name__icontains=search_query) |
            Q(provider__full_name__icontains=search_query) |
            Q(service__name__icontains=search_query)
        )
    bookings = bookings.order_by('-created_at')
    reviews = Review.objects.all().select_related('customer', 'provider', 'booking', 'booking__service').order_by('-created_at')
    review_stats = review_dashboard_statistics()
    payments = Payment.objects.select_related('booking', 'booking__customer', 'booking__service').order_by('-created_at')

    commission_rate = request.session.get('commission_rate', 15.0)
    if request.method == 'POST' and 'update_settings' in request.POST:
        new_rate = request.POST.get('commission_rate')
        if new_rate:
            try:
                commission_rate = float(new_rate)
                request.session['commission_rate'] = commission_rate
                messages.success(request, 'Platform settings updated successfully!')
            except ValueError:
                messages.error(request, 'Invalid commission rate value.')
        return redirect('admin_dashboard')

    total_users = users.count()
    total_providers = providers.count()
    total_customers = User.objects.filter(role=User.Role.CUSTOMER).count()
    total_bookings = bookings.count()
    completed_bookings = bookings.filter(status=Booking.Status.COMPLETED).count()
    pending_bookings = bookings.filter(status=Booking.Status.PENDING).count()
    accepted_bookings = bookings.filter(status=Booking.Status.ACCEPTED).count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
    total_revenue = payments.filter(payment_status=Payment.Status.PAID).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    successful_payments = payments.filter(payment_status=Payment.Status.PAID).count()
    failed_payments = payments.filter(payment_status=Payment.Status.FAILED).count()
    recent_transactions = payments[:10]
    platform_earnings = total_revenue * (Decimal(str(commission_rate)) / Decimal('100'))

    context = {
        'users': users,
        'providers': providers,
        'bookings': bookings,
        'reviews': reviews,
        'review_stats': review_stats,
        'commission_rate': commission_rate,
        'search_query': search_query,
        'selected_status': status_filter if status_filter in Booking.Status.values else 'all',
        'analytics': {
            'total_users': total_users,
            'total_providers': total_providers,
            'total_customers': total_customers,
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'pending_bookings': pending_bookings,
            'accepted_bookings': accepted_bookings,
            'avg_rating': round(avg_rating, 1),
            'total_reviews': review_stats['total_reviews'],
            'average_platform_rating': review_stats['average_platform_rating'],
            'total_revenue': total_revenue,
            'successful_payments': successful_payments,
            'failed_payments': failed_payments,
            'platform_earnings': platform_earnings,
        },
        'recent_transactions': recent_transactions,
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
@role_required('PROVIDER')
def add_service(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save(commit=False)
            service.provider = request.user
            service.save()
            messages.success(request, f"Service '{service.title}' added successfully!")
        else:
            messages.error(request, 'Failed to add service. Check details and try again.')
    return redirect('provider_dashboard')


@login_required
@role_required('PROVIDER')
def edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, provider=request.user)
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service '{service.title}' updated successfully!")
        else:
            messages.error(request, 'Failed to update service.')
    return redirect('provider_dashboard')


@login_required
@role_required('PROVIDER')
def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, provider=request.user)
    service.delete()
    messages.success(request, 'Service deleted successfully.')
    return redirect('provider_dashboard')


@login_required
@role_required('CUSTOMER')
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, is_available=True)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if service.provider == request.user:
            messages.error(request, 'You cannot book your own service.')
            return redirect('service_detail', pk=service_id)

        if form.is_valid():
            with transaction.atomic():
                booking = form.save(commit=False)
                booking.customer = request.user
                booking.service = service
                booking.provider = service.provider
                booking.status = Booking.Status.PENDING
                booking.save()
                payment = Payment.objects.create(
                    booking=booking,
                    amount=service.price,
                    payment_status=Payment.Status.PENDING,
                )

            try:
                checkout_session = create_checkout_session(request, payment)
            except ImproperlyConfigured as exc:
                logger.exception('Stripe checkout configuration error for payment_id=%s', payment.id)
                _mark_payment_failed(payment)
                messages.error(request, str(exc))
                return redirect('service_detail', pk=service_id)
            except Exception:
                logger.exception('Stripe checkout creation failed for payment_id=%s', payment.id)
                _mark_payment_failed(payment)
                messages.error(request, 'Unable to start secure checkout right now. Please try again.')
                return redirect('payment_cancel', payment_id=payment.id)

            payment.stripe_payment_id = checkout_session.id
            payment.save(update_fields=['stripe_payment_id'])
            logger.info('Stripe Checkout session created for booking_id=%s payment_id=%s', booking.id, payment.id)
            return redirect(checkout_session.url)

        messages.error(request, 'Failed to submit booking. Select a valid future date and time.')
    else:
        messages.error(request, 'Booking requests must be submitted via the service detail page.')

    return redirect('service_detail', pk=service_id)


@login_required
@role_required('CUSTOMER')
def payment_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, 'Missing payment session details.')
        return redirect('customer_dashboard')

    payment = get_object_or_404(
        Payment.objects.select_related('booking', 'booking__service', 'booking__provider'),
        stripe_payment_id=session_id,
        booking__customer=request.user,
    )

    try:
        stripe = get_stripe_module()
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        logger.exception('Unable to verify Stripe session_id=%s on success return', session_id)
        messages.warning(request, 'Payment verification is still pending. We will update your booking shortly.')
        return render(request, 'accounts/payment_success.html', {'payment': payment, 'booking': payment.booking})

    if session.payment_status == 'paid':
        _mark_payment_paid(payment, getattr(session, 'payment_intent', '') or session_id)
        payment.refresh_from_db()
        messages.success(request, 'Payment successful. Your booking is confirmed.')
    else:
        logger.warning('Stripe success return had non-paid status=%s for payment_id=%s', session.payment_status, payment.id)
        messages.info(request, 'Payment is still processing. Your booking will confirm after Stripe completes it.')

    return render(request, 'accounts/payment_success.html', {'payment': payment, 'booking': payment.booking})


@login_required
@role_required('CUSTOMER')
def payment_cancel(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('booking', 'booking__service'),
        id=payment_id,
        booking__customer=request.user,
    )
    messages.info(request, 'Payment was cancelled. Your booking is not confirmed yet.')
    return render(request, 'accounts/payment_cancel.html', {'payment': payment, 'booking': payment.booking})


@login_required
@role_required('CUSTOMER')
@require_POST
def retry_payment(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('booking', 'booking__service'),
        id=payment_id,
        booking__customer=request.user,
    )

    if payment.payment_status == Payment.Status.PAID:
        messages.info(request, 'This booking has already been paid.')
        return redirect('customer_dashboard')

    payment.payment_status = Payment.Status.PENDING
    payment.save(update_fields=['payment_status'])

    try:
        checkout_session = create_checkout_session(request, payment)
    except Exception:
        logger.exception('Stripe retry checkout failed for payment_id=%s', payment.id)
        _mark_payment_failed(payment)
        messages.error(request, 'Unable to restart checkout. Please try again.')
        return redirect('payment_cancel', payment_id=payment.id)

    payment.stripe_payment_id = checkout_session.id
    payment.save(update_fields=['stripe_payment_id'])
    return redirect(checkout_session.url)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error('Stripe webhook secret is not configured.')
        return HttpResponse(status=500)

    try:
        stripe = get_stripe_module()
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        logger.warning('Stripe webhook received invalid payload.')
        return HttpResponse(status=400)
    except Exception:
        logger.exception('Stripe webhook signature validation failed.')
        return HttpResponse(status=400)

    event_type = event.get('type')
    event_object = event.get('data', {}).get('object', {})
    logger.info('Stripe webhook received: %s', event_type)

    if event_type == 'checkout.session.completed':
        payment_id = event_object.get('metadata', {}).get('payment_id')
        if payment_id:
            payment = Payment.objects.filter(pk=payment_id).first()
            if payment:
                _mark_payment_paid(payment, event_object.get('payment_intent') or event_object.get('id', ''))
            else:
                logger.error('Webhook payment_id=%s did not match a local payment.', payment_id)
    elif event_type == 'payment_intent.payment_failed':
        payment_id = event_object.get('metadata', {}).get('payment_id')
        if payment_id:
            payment = Payment.objects.filter(pk=payment_id).first()
            if payment:
                _mark_payment_failed(payment)
    elif event_type == 'charge.refunded':
        payment_id = event_object.get('metadata', {}).get('payment_id')
        payment = Payment.objects.filter(pk=payment_id).first() if payment_id else None
        if payment:
            payment.payment_status = Payment.Status.REFUNDED
            payment.save(update_fields=['payment_status'])
            logger.info('Payment refunded for payment_id=%s', payment.id)

    return JsonResponse({'status': 'ok'})


@login_required
def update_booking_status(request, booking_id, status):
    if request.user.role not in [User.Role.PROVIDER, User.Role.ADMIN]:
        messages.error(request, 'Access Denied.')
        return redirect('dashboard_redirect')

    if request.user.role == User.Role.PROVIDER:
        booking = get_object_or_404(Booking, id=booking_id, provider=request.user)
    else:
        booking = get_object_or_404(Booking, id=booking_id)

    if status in Booking.Status.values:
        booking.status = status
        booking.save()
        messages.success(request, f"Booking status updated to: {booking.get_status_display()}")
    else:
        messages.error(request, 'Invalid status chosen.')

    return redirect('dashboard_redirect')


@login_required
def send_chat_message(request, receiver_id):
    receiver = get_object_or_404(User, id=receiver_id)

    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            ChatMessage.objects.create(sender=request.user, receiver=receiver, message=message_text)
        else:
            messages.error(request, 'Message cannot be empty.')

    if request.user.role == User.Role.CUSTOMER:
        return redirect(f'/customer-dashboard/?chat_with={receiver_id}#chat-section')
    return redirect(f'/provider-dashboard/?chat_with={receiver_id}#chat-section')


@login_required
@role_required('ADMIN')
def admin_toggle_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
    else:
        user.is_active = not user.is_active
        user.save()
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.full_name} has been {status}.')
    return redirect('admin_dashboard')


@login_required
@role_required('ADMIN')
def admin_delete_review(request, review_id):
    messages.error(request, 'Direct admin review deletion is disabled.')
    return redirect('admin_dashboard')
