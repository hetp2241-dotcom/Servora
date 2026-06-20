from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import Category, ProviderProfile, Service, Booking, Payment, ChatMessage

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ('email', 'full_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone_number', 'role', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'city', 'experience_years', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'city')
    search_fields = ('full_name', 'user__full_name', 'city')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'category', 'price', 'duration', 'is_available', 'created_at')
    list_filter = ('category', 'is_available')
    search_fields = ('title', 'description', 'provider__full_name')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'provider', 'service', 'booking_date', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('customer__full_name', 'provider__full_name', 'service__title')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'stripe_payment_id', 'amount', 'payment_status', 'created_at')
    list_filter = ('payment_status',)
    search_fields = ('stripe_payment_id', 'booking__customer__full_name', 'booking__service__name')
    readonly_fields = ('created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'timestamp')
    search_fields = ('sender__full_name', 'receiver__full_name', 'message')
