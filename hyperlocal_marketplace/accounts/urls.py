from django.urls import path
from . import views

urlpatterns = [
    path('', views.ServiceListView.as_view(), name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect_view, name='dashboard_redirect'),
    path('customer-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('provider-dashboard/', views.provider_dashboard, name='provider_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('services/<int:pk>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('providers/', views.ProviderProfileListView.as_view(), name='provider_profile_list'),
    path('providers/<int:pk>/', views.ProviderProfileDetailView.as_view(), name='provider_profile_detail'),
    path('providers/edit/', views.provider_profile_edit, name='provider_profile_edit'),
    
    # Provider actions
    path('services/add/', views.add_service, name='add_service'),
    path('services/edit/<int:service_id>/', views.edit_service, name='edit_service'),
    path('services/delete/<int:service_id>/', views.delete_service, name='delete_service'),
    
    # Booking actions
    path('book-service/<int:service_id>/', views.book_service, name='book_service'),
    path('bookings/status/<int:booking_id>/<str:status>/', views.update_booking_status, name='update_booking_status'),
    
    # Review action
    path('bookings/review/<int:booking_id>/', views.add_review, name='add_review'),
    
    # Chat action
    path('chat/send/<int:receiver_id>/', views.send_chat_message, name='send_chat_message'),
    
    # Admin actions
    path('admin/toggle-user/<int:user_id>/', views.admin_toggle_user, name='admin_toggle_user'),
    path('admin/delete-review/<int:review_id>/', views.admin_delete_review, name='admin_delete_review'),
]
