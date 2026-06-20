from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('', views.ReviewListView.as_view(), name='list'),
    path('booking/<int:booking_id>/create/', views.CreateReviewView.as_view(), name='create'),
    path('<int:pk>/edit/', views.UpdateReviewView.as_view(), name='update'),
    path('<int:pk>/delete/', views.DeleteReviewView.as_view(), name='delete'),
    path('providers/<int:pk>/summary/', views.ProviderRatingSummaryView.as_view(), name='provider_summary'),
]
