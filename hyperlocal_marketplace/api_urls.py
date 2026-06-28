from django.urls import path

from hyperlocal_marketplace import api


app_name = "api"

urlpatterns = [
    path("", api.api_index, name="index"),
    path("csrf/", api.csrf_token, name="csrf"),
    path("auth/session/", api.session_detail, name="session"),
    path("auth/login/", api.login_api, name="login"),
    path("auth/register/", api.register_api, name="register"),
    path("auth/logout/", api.logout_api, name="logout"),
    path("categories/", api.categories_api, name="categories"),
    path("services/", api.services_api, name="services"),
    path("services/<int:service_id>/", api.service_detail_api, name="service-detail"),
    path("providers/", api.providers_api, name="providers"),
    path("providers/<int:profile_id>/", api.provider_detail_api, name="provider-detail"),
    path("profile/", api.profile_api, name="profile"),
    path("dashboard/", api.dashboard_api, name="dashboard"),
    path("bookings/", api.bookings_api, name="bookings"),
    path("bookings/<int:booking_id>/status/", api.booking_status_api, name="booking-status"),
    path("payments/", api.payments_api, name="payments"),
    path("payments/<int:payment_id>/retry/", api.payment_retry_api, name="payment-retry"),
    path("reviews/", api.reviews_api, name="reviews"),
    path("reviews/<int:review_id>/", api.review_detail_api, name="review-detail"),
    path("providers/<int:provider_id>/rating/", api.provider_rating_api, name="provider-rating"),
    path("notifications/", api.notifications_api, name="notifications"),
    path("notifications/<int:notification_id>/read/", api.notification_read_api, name="notification-read"),
    path("messages/", api.messages_api, name="messages"),
    path("messages/<int:partner_id>/", api.conversation_api, name="conversation"),
    path("maps/providers/", api.provider_locations_api, name="provider-locations"),
]
