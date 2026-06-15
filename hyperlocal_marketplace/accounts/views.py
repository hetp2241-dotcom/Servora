from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q
from django.utils import timezone
from django.views.generic import ListView, DetailView
from .forms import (
    CustomUserCreationForm,
    CustomLoginForm,
    ProviderProfileForm,
    ServiceForm,
    BookingForm,
    ReviewForm,
    ServiceFilterForm,
)
from .models import (
    User,
    Category,
    ProviderProfile,
    Service,
    Booking,
    Review,
    ChatMessage,
)
from .decorators import role_required


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
        queryset = Service.objects.select_related('provider', 'category', 'provider__provider_profile')
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
    bookings = Booking.objects.filter(customer=request.user).select_related('service', 'provider').order_by('-created_at')
    providers = User.objects.filter(role=User.Role.PROVIDER)
    review_form = ReviewForm()

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

    context = {
        'services': services,
        'bookings': bookings,
        'providers': providers,
        'chat_partner': chat_partner,
        'chat_messages': chat_messages,
        'review_form': review_form,
    }
    return render(request, 'accounts/customer_dashboard.html', context)


@login_required
@role_required('PROVIDER')
def provider_dashboard(request):
    profile = get_object_or_404(ProviderProfile, user=request.user)
    services = Service.objects.filter(provider=request.user).select_related('category').order_by('-created_at')
    bookings = Booking.objects.filter(provider=request.user).select_related('service', 'customer').order_by('-created_at')
    service_form = ServiceForm()
    categories = Category.objects.all()

    total_services = services.count()
    active_services = services.filter(is_available=True).count()
    recent_services = services[:4]
    profile_completion = profile.completion_percentage

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
    }
    return render(request, 'accounts/provider_dashboard.html', context)


@login_required
@role_required('ADMIN')
def admin_dashboard(request):
    users = User.objects.all().order_by('-date_joined')
    providers = User.objects.filter(role=User.Role.PROVIDER)
    bookings = Booking.objects.all().select_related('customer', 'provider', 'service').order_by('-created_at')
    reviews = Review.objects.all().select_related('customer', 'provider', 'booking').order_by('-created_at')

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
    total_revenue = sum(b.service.price for b in bookings if b.status == Booking.Status.COMPLETED)
    platform_earnings = total_revenue * (Decimal(str(commission_rate)) / Decimal('100'))

    context = {
        'users': users,
        'providers': providers,
        'bookings': bookings,
        'reviews': reviews,
        'commission_rate': commission_rate,
        'analytics': {
            'total_users': total_users,
            'total_providers': total_providers,
            'total_customers': total_customers,
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'pending_bookings': pending_bookings,
            'accepted_bookings': accepted_bookings,
            'avg_rating': round(avg_rating, 1),
            'total_revenue': total_revenue,
            'platform_earnings': platform_earnings,
        },
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
        if form.is_valid():
            booking = form.save(commit=False)
            booking.customer = request.user
            booking.service = service
            booking.provider = service.provider
            booking.status = Booking.Status.PENDING
            booking.save()
            messages.success(request, f"Booking request for '{service.title}' sent successfully!")
        else:
            messages.error(request, 'Failed to submit booking. Select a valid date and time.')

    return redirect('service_detail', pk=service_id)


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
@role_required('CUSTOMER')
def add_review(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if booking.status not in [Booking.Status.COMPLETED, Booking.Status.ACCEPTED]:
        messages.error(request, 'You can only write a review for an active or completed booking.')
        return redirect('customer_dashboard')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.update_or_create(
                booking=booking,
                defaults={
                    'customer': request.user,
                    'provider': booking.provider,
                    'rating': form.cleaned_data['rating'],
                    'comment': form.cleaned_data['comment'],
                },
            )
            messages.success(request, 'Review submitted successfully!')
        else:
            messages.error(request, 'Failed to submit review. Rating must be 1-5.')

    return redirect('customer_dashboard')


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
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    return redirect('admin_dashboard')
