"""Additive JSON adapters for the existing Servora application.

Read endpoints serialize the existing ORM querysets. Mutating endpoints validate with
the existing forms or delegate to the existing Django views so the template UI and
the React UI share one source of business behavior.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.messages import get_messages
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from hyperlocal_marketplace.accounts import views as account_views
from hyperlocal_marketplace.accounts.forms import CustomLoginForm, CustomUserCreationForm
from hyperlocal_marketplace.accounts.models import (
    Booking,
    Category,
    ChatMessage,
    Notification,
    Payment,
    ProviderProfile,
    Service,
    User,
)
from hyperlocal_marketplace.reviews.models import Review
from hyperlocal_marketplace.reviews.services import dashboard_statistics, provider_statistics
from hyperlocal_marketplace.reviews.views import CreateReviewView, DeleteReviewView, ReviewListView, UpdateReviewView


def _json_error(message, *, status=400, errors=None):
    payload = {"ok": False, "error": message}
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def _form_errors(form):
    return {field: [str(error) for error in values] for field, values in form.errors.items()}


def _messages(request):
    return [{"level": item.tags or "info", "message": str(item)} for item in get_messages(request)]


def api_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _json_error("Authentication required.", status=401)
        return view(request, *args, **kwargs)

    return wrapped


def api_role_required(*roles):
    def decorator(view):
        @wraps(view)
        @api_login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                return _json_error("You do not have permission to perform this action.", status=403)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


def _absolute_media(request, url):
    return request.build_absolute_uri(url) if url else ""


def _user_data(user):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number or "",
        "role": user.role,
        "is_active": user.is_active,
        "date_joined": user.date_joined.isoformat(),
    }


def _rating_data(provider):
    stats = provider_statistics(provider)
    return {
        "average_rating": float(stats["average_rating"]),
        "review_count": int(stats["review_count"]),
        "distribution": {str(key): value for key, value in stats["distribution"].items()},
    }


def _profile_data(request, profile, *, include_services=False):
    rating = _rating_data(profile.user)
    data = {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": profile.full_name or profile.user.full_name,
        "phone_number": profile.phone_number or "",
        "address": profile.address or "",
        "city": profile.city or "",
        "latitude": float(profile.latitude),
        "longitude": float(profile.longitude),
        "experience_years": profile.experience_years,
        "description": profile.description or "",
        "is_verified": profile.is_verified,
        "profile_picture_url": _absolute_media(request, profile.profile_picture_url),
        "completion_percentage": profile.completion_percentage,
        "member_since": profile.created_at.isoformat(),
        "jobs_completed": Booking.objects.filter(provider=profile.user, status=Booking.Status.COMPLETED).count(),
        **rating,
    }
    if include_services:
        data["services"] = [
            _service_data(request, service)
            for service in profile.user.services.filter(is_available=True).select_related(
                "category", "provider", "provider__provider_profile"
            )
        ]
    return data


def _service_data(request, service, *, include_reviews=False):
    profile = getattr(service.provider, "provider_profile", None)
    avg = getattr(service, "avg_rating", None)
    count = getattr(service, "review_count", None)
    if avg is None or count is None:
        stats = provider_statistics(service.provider)
        avg = stats["average_rating"]
        count = stats["review_count"]
    data = {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "price": str(service.price),
        "duration_hours": service.duration_hours,
        "image_url": _absolute_media(request, service.image_url),
        "is_available": service.is_available,
        "created_at": service.created_at.isoformat(),
        "category": ({"id": service.category_id, "name": service.category.name} if service.category else None),
        "provider": {
            "id": service.provider_id,
            "profile_id": profile.id if profile else None,
            "full_name": service.provider.full_name,
            "city": profile.city if profile else "",
            "is_verified": profile.is_verified if profile else False,
            "profile_picture_url": _absolute_media(request, profile.profile_picture_url) if profile else "",
        },
        "average_rating": float(avg or 0),
        "review_count": int(count or 0),
    }
    if include_reviews:
        data["reviews"] = [
            _review_data(review)
            for review in Review.objects.filter(booking__service=service).select_related(
                "booking", "booking__service", "customer", "provider"
            )[:20]
        ]
    return data


def _payment_data(payment):
    return {
        "id": payment.id,
        "booking_id": payment.booking_id,
        "amount": str(payment.amount),
        "payment_status": payment.payment_status,
        "stripe_session_id": payment.stripe_payment_id or "",
        "created_at": payment.created_at.isoformat(),
        "service_name": payment.booking.service.name,
    }


def _booking_data(booking):
    payments = list(booking.payments.all())
    review = getattr(booking, "marketplace_review", None)
    return {
        "id": booking.id,
        "booking_date": booking.booking_date.isoformat(),
        "notes": booking.notes or "",
        "status": booking.status,
        "status_label": booking.get_status_display(),
        "created_at": booking.created_at.isoformat(),
        "service": {"id": booking.service_id, "name": booking.service.name, "price": str(booking.service.price)},
        "customer": {"id": booking.customer_id, "full_name": booking.customer.full_name},
        "provider": {"id": booking.provider_id, "full_name": booking.provider.full_name},
        "payment": _payment_data(payments[0]) if payments else None,
        "has_review": bool(review),
        "review_id": review.id if review else None,
    }


def _review_data(review):
    return {
        "id": review.id,
        "booking_id": review.booking_id,
        "service": {"id": review.booking.service_id, "name": review.booking.service.name},
        "customer": {"id": review.customer_id, "full_name": review.customer.full_name},
        "provider": {"id": review.provider_id, "full_name": review.provider.full_name},
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
        "updated_at": review.updated_at.isoformat(),
    }


def _notification_data(notification):
    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "link": notification.link,
        "created_at": notification.created_at.isoformat(),
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "actor": ({"id": notification.actor_id, "full_name": notification.actor.full_name} if notification.actor else None),
    }


def _message_data(message):
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "message": message.message,
        "timestamp": message.timestamp.isoformat(),
    }


def _paginate(request, queryset, serializer, *, default_size=12):
    try:
        size = min(max(int(request.GET.get("page_size", default_size)), 1), 100)
        page_number = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        return None, _json_error("Invalid pagination values.")
    paginator = Paginator(queryset, size)
    page = paginator.get_page(page_number)
    return {
        "results": [serializer(item) for item in page.object_list],
        "pagination": {
            "page": page.number,
            "page_size": size,
            "count": paginator.count,
            "pages": paginator.num_pages,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        },
    }, None


@require_GET
def api_index(request):
    return JsonResponse({
        "name": "Servora API",
        "version": "1",
        "authentication": "Django session + CSRF",
        "websockets": {"chat": "/ws/chat/<partner_id>/", "notifications": "/ws/notifications/"},
    })


@ensure_csrf_cookie
@require_GET
def csrf_token(request):
    return JsonResponse({"ok": True})


@require_GET
def session_detail(request):
    return JsonResponse({"authenticated": request.user.is_authenticated, "user": _user_data(request.user) if request.user.is_authenticated else None})


@require_POST
def login_api(request):
    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "user": _user_data(request.user)})
    form = CustomLoginForm(request, data=request.POST)
    if not form.is_valid():
        return _json_error("Invalid email or password.", status=400, errors=_form_errors(form))

    user = form.get_user()
    login(request, user)
    request.session.set_expiry(1209600 if form.cleaned_data.get("remember_me") else 0)
    return JsonResponse({"ok": True, "user": _user_data(user)})



@require_POST
def register_api(request):
    if request.user.is_authenticated:
        return _json_error("Log out before creating another account.", status=409)
    form = CustomUserCreationForm(request.POST)
    if not form.is_valid():
        return _json_error("Registration failed.", status=400, errors=_form_errors(form))
    user = form.save()
    return JsonResponse({"ok": True, "user": _user_data(user)}, status=201)


@require_POST
@api_login_required
def logout_api(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def categories_api(request):
    categories = [
        {"id": category.id, "name": category.name, "description": category.description, "image_url": _absolute_media(request, category.image_url)}
        for category in Category.objects.all()
    ]
    return JsonResponse({"results": categories})


@require_http_methods(["GET", "POST"])
def services_api(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return _json_error("Authentication required.", status=401)
        if request.user.role != User.Role.PROVIDER:
            return _json_error("Provider account required.", status=403)
        before = Service.objects.filter(provider=request.user).count()
        account_views.add_service(request)
        created = Service.objects.filter(provider=request.user).select_related("category", "provider", "provider__provider_profile").first()
        api_messages = _messages(request)
        if Service.objects.filter(provider=request.user).count() == before:
            return JsonResponse({"ok": False, "messages": api_messages}, status=400)
        return JsonResponse({"ok": True, "service": _service_data(request, created), "messages": api_messages}, status=201)

    view = account_views.ServiceListView()
    view.request = request
    queryset = view.get_queryset()
    payload, error = _paginate(request, queryset, lambda item: _service_data(request, item))
    if error:
        return error
    payload["filters"] = {
        "categories": list(Category.objects.values("id", "name")),
        "cities": list(ProviderProfile.objects.exclude(city="").values_list("city", flat=True).distinct().order_by("city")),
    }
    return JsonResponse(payload)


@require_http_methods(["GET", "POST", "DELETE"])
def service_detail_api(request, service_id):
    service = get_object_or_404(Service.objects.select_related("category", "provider", "provider__provider_profile"), pk=service_id)
    if request.method == "GET":
        data = _service_data(request, service, include_reviews=True)
        data["related_services"] = [
            _service_data(request, item)
            for item in service.provider.services.filter(is_available=True).exclude(pk=service.id).select_related(
                "category", "provider", "provider__provider_profile"
            )[:4]
        ]
        return JsonResponse(data)
    if not request.user.is_authenticated:
        return _json_error("Authentication required.", status=401)
    if request.user != service.provider:
        return _json_error("Only the service owner can modify it.", status=403)
    if request.method == "DELETE":
        account_views.delete_service(request, service_id)
        return JsonResponse({"ok": True, "messages": _messages(request)})
    account_views.edit_service(request, service_id)
    service.refresh_from_db()
    return JsonResponse({"ok": True, "service": _service_data(request, service), "messages": _messages(request)})


@require_GET
def providers_api(request):
    queryset = ProviderProfile.objects.select_related("user", "user__rating_stats").order_by("-is_verified", "full_name")
    city = request.GET.get("city", "").strip()
    search = request.GET.get("search", "").strip()
    if city:
        queryset = queryset.filter(city__iexact=city)
    if search:
        queryset = queryset.filter(Q(full_name__icontains=search) | Q(description__icontains=search) | Q(user__services__name__icontains=search)).distinct()
    payload, error = _paginate(request, queryset, lambda item: _profile_data(request, item))
    return error or JsonResponse(payload)


@require_GET
def provider_detail_api(request, profile_id):
    profile = get_object_or_404(ProviderProfile.objects.select_related("user", "user__rating_stats"), pk=profile_id)
    data = _profile_data(request, profile, include_services=True)
    stats = provider_statistics(profile.user)
    data["latest_reviews"] = [_review_data(item) for item in stats["latest_reviews"]]
    return JsonResponse(data)


@require_http_methods(["GET", "POST"])
@api_login_required
def profile_api(request):
    if request.method == "GET":
        data = _user_data(request.user)
        profile = getattr(request.user, "provider_profile", None)
        data["provider_profile"] = _profile_data(request, profile) if profile else None
        return JsonResponse(data)
    if request.user.role != User.Role.PROVIDER:
        return _json_error("Only provider profiles are editable here.", status=403)
    account_views.provider_profile_edit(request)
    profile = ProviderProfile.objects.select_related("user").get(user=request.user)
    return JsonResponse({"ok": True, "profile": _profile_data(request, profile), "messages": _messages(request)})


@require_GET
@api_login_required
def dashboard_api(request):
    user = request.user
    bookings = Booking.objects.filter(Q(customer=user) if user.role == User.Role.CUSTOMER else Q(provider=user)).select_related(
        "service", "customer", "provider"
    ).prefetch_related("payments", "marketplace_review")
    if user.role == User.Role.CUSTOMER:
        payments = Payment.objects.filter(booking__customer=user)
        return JsonResponse({
            "role": user.role,
            "stats": {
                "total_bookings": bookings.count(),
                "upcoming": bookings.filter(status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.ACCEPTED]).count(),
                "completed": bookings.filter(status=Booking.Status.COMPLETED).count(),
                "total_spent": str(payments.filter(payment_status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0),
            },
            "recent_bookings": [_booking_data(item) for item in bookings[:5]],
        })
    if user.role == User.Role.PROVIDER:
        services = Service.objects.filter(provider=user)
        stats = provider_statistics(user)
        return JsonResponse({
            "role": user.role,
            "stats": {
                "total_services": services.count(),
                "active_services": services.filter(is_available=True).count(),
                "total_bookings": bookings.count(),
                "completed": bookings.filter(status=Booking.Status.COMPLETED).count(),
                "average_rating": float(stats["average_rating"]),
                "review_count": stats["review_count"],
                "earnings": str(Payment.objects.filter(booking__provider=user, payment_status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0),
            },
            "recent_bookings": [_booking_data(item) for item in bookings[:5]],
        })
    platform = dashboard_statistics()
    return JsonResponse({
        "role": user.role,
        "stats": {
            "users": User.objects.count(),
            "providers": User.objects.filter(role=User.Role.PROVIDER).count(),
            "bookings": Booking.objects.count(),
            "completed": Booking.objects.filter(status=Booking.Status.COMPLETED).count(),
            "total_reviews": platform["total_reviews"],
            "average_rating": float(platform["average_platform_rating"]),
        },
    })


@require_http_methods(["GET", "POST"])
@api_login_required
def bookings_api(request):
    if request.method == "POST":
        if request.user.role != User.Role.CUSTOMER:
            return _json_error("Customer account required.", status=403)
        service_id = request.POST.get("service_id")
        if not service_id:
            return _json_error("service_id is required.")
        response = account_views.book_service(request, service_id)
        api_messages = _messages(request)
        checkout_url = getattr(response, "url", "")
        booking = Booking.objects.filter(customer=request.user, service_id=service_id).select_related(
            "service", "customer", "provider"
        ).prefetch_related("payments", "marketplace_review").first()
        if not checkout_url.startswith("http"):
            return JsonResponse({"ok": False, "messages": api_messages}, status=400)
        return JsonResponse({"ok": True, "checkout_url": checkout_url, "booking": _booking_data(booking), "messages": api_messages}, status=201)

    queryset = Booking.objects.select_related("service", "customer", "provider").prefetch_related("payments", "marketplace_review")
    if request.user.role == User.Role.CUSTOMER:
        queryset = queryset.filter(customer=request.user)
    elif request.user.role == User.Role.PROVIDER:
        queryset = queryset.filter(provider=request.user)
    status = request.GET.get("status", "").upper()
    if status in Booking.Status.values:
        queryset = queryset.filter(status=status)
    payload, error = _paginate(request, queryset, _booking_data)
    return error or JsonResponse(payload)


@require_POST
@api_role_required(User.Role.PROVIDER, User.Role.ADMIN)
def booking_status_api(request, booking_id):
    status = request.POST.get("status", "").upper()
    account_views.update_booking_status(request, booking_id, status)
    booking = get_object_or_404(Booking.objects.select_related("service", "customer", "provider").prefetch_related("payments", "marketplace_review"), pk=booking_id)
    return JsonResponse({"ok": booking.status == status, "booking": _booking_data(booking), "messages": _messages(request)})


@require_GET
@api_login_required
def payments_api(request):
    queryset = Payment.objects.select_related("booking", "booking__service", "booking__customer", "booking__provider")
    if request.user.role == User.Role.CUSTOMER:
        queryset = queryset.filter(booking__customer=request.user)
    elif request.user.role == User.Role.PROVIDER:
        queryset = queryset.filter(booking__provider=request.user)
    payload, error = _paginate(request, queryset, _payment_data)
    return error or JsonResponse(payload)


@require_POST
@api_role_required(User.Role.CUSTOMER)
def payment_retry_api(request, payment_id):
    response = account_views.retry_payment(request, payment_id)
    checkout_url = getattr(response, "url", "")
    api_messages = _messages(request)
    if not checkout_url.startswith("http"):
        return JsonResponse({"ok": False, "messages": api_messages}, status=400)
    return JsonResponse({"ok": True, "checkout_url": checkout_url, "messages": api_messages})


@require_http_methods(["GET", "POST"])
@api_login_required
def reviews_api(request):
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        if not booking_id:
            return _json_error("booking_id is required.")
        response = CreateReviewView.as_view()(request, booking_id=int(booking_id))
        api_messages = _messages(request)
        review = Review.objects.filter(booking_id=booking_id, customer=request.user).select_related("booking", "booking__service", "customer", "provider").first()
        if not review or response.status_code >= 400:
            return JsonResponse({"ok": False, "messages": api_messages}, status=400)
        return JsonResponse({"ok": True, "review": _review_data(review), "messages": api_messages}, status=201)

    view = ReviewListView()
    view.request = request
    queryset = view.get_queryset()
    payload, error = _paginate(request, queryset, _review_data, default_size=10)
    return error or JsonResponse(payload)


@require_http_methods(["POST", "DELETE"])
@api_role_required(User.Role.CUSTOMER)
def review_detail_api(request, review_id):
    if request.method == "DELETE":
        DeleteReviewView.as_view()(request, pk=review_id)
        return JsonResponse({"ok": True, "messages": _messages(request)})
    response = UpdateReviewView.as_view()(request, pk=review_id)
    review = Review.objects.filter(pk=review_id, customer=request.user).select_related("booking", "booking__service", "customer", "provider").first()
    if not review or response.status_code >= 400:
        return JsonResponse({"ok": False, "messages": _messages(request)}, status=400)
    return JsonResponse({"ok": True, "review": _review_data(review), "messages": _messages(request)})


@require_GET
def provider_rating_api(request, provider_id):
    provider = get_object_or_404(User, pk=provider_id, role=User.Role.PROVIDER)
    return JsonResponse({"provider_id": provider.id, **_rating_data(provider)})


@require_GET
@api_login_required
def notifications_api(request):
    queryset = Notification.objects.filter(recipient=request.user).select_related("actor")
    unread_only = request.GET.get("unread") in {"1", "true", "yes"}
    if unread_only:
        queryset = queryset.filter(read_at__isnull=True)
    payload, error = _paginate(request, queryset, _notification_data, default_size=20)
    if error:
        return error
    payload["unread_count"] = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    return JsonResponse(payload)


@require_POST
@api_login_required
def notification_read_api(request, notification_id):
    return account_views.mark_notification_as_read(request, notification_id)


@require_GET
@api_login_required
def messages_api(request):
    partner_ids = set(
        ChatMessage.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).values_list("sender_id", "receiver_id")
    )
    flattened = {item for pair in partner_ids for item in pair if item != request.user.id}
    if request.user.role == User.Role.CUSTOMER:
        flattened.update(Booking.objects.filter(customer=request.user).values_list("provider_id", flat=True))
        role = User.Role.PROVIDER
    elif request.user.role == User.Role.PROVIDER:
        flattened.update(Booking.objects.filter(provider=request.user).values_list("customer_id", flat=True))
        role = User.Role.CUSTOMER
    else:
        role = None
    users = User.objects.filter(id__in=flattened)
    if role:
        users = users.filter(role=role)
    return JsonResponse({"results": [_user_data(user) for user in users.order_by("full_name")]})


@require_GET
@api_login_required
def conversation_api(request, partner_id):
    partner = get_object_or_404(User, pk=partner_id)
    queryset = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user)
    ).order_by("timestamp")
    return JsonResponse({
        "partner": _user_data(partner),
        "messages": [_message_data(item) for item in queryset],
        "websocket_url": f"/ws/chat/{partner.id}/",
    })


@require_GET
def provider_locations_api(request):
    profiles = ProviderProfile.objects.select_related("user", "user__rating_stats").exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    return JsonResponse({
        "results": [
            {
                "profile_id": profile.id,
                "provider_id": profile.user_id,
                "provider_name": profile.full_name or profile.user.full_name,
                "latitude": float(profile.latitude),
                "longitude": float(profile.longitude),
                "address": profile.address or "",
                "city": profile.city or "",
                "is_verified": profile.is_verified,
                **_rating_data(profile.user),
            }
            for profile in profiles
        ]
    })
