from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Category, ProviderProfile, Service, Booking, Review

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (User.Role.CUSTOMER, 'Customer'),
            (User.Role.PROVIDER, 'Service Provider')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=User.Role.CUSTOMER
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. +1 (555) 019-2834', 'class': 'form-control'})
    )
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Jane Doe', 'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'name@example.com', 'class': 'form-control'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('full_name', 'email', 'phone_number', 'role')

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('full_name', 'email', 'phone_number', 'role', 'is_active', 'is_staff')


class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'id': 'login-email'
        }),
        label='Email Address'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'id': 'login-password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'remember-me'
        })
    )


class ProviderProfileForm(forms.ModelForm):
    class Meta:
        model = ProviderProfile
        fields = [
            'profile_picture',
            'full_name',
            'phone_number',
            'address',
            'city',
            'experience_years',
            'description',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Introduce your skills and experience', 'rows': 4}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['category', 'name', 'description', 'price', 'duration_hours', 'image', 'is_available']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Full House Plumbing Service'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Describe the service offering clearly', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Estimated duration in hours', 'min': 1}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BookingForm(forms.ModelForm):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Add any details or special notes for the provider', 'rows': 3}
        ),
        label='Additional Notes',
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'notes']
        widgets = {
            'booking_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_booking_date(self):
        booking_date = self.cleaned_data.get('booking_date')
        if booking_date and booking_date <= timezone.now():
            raise forms.ValidationError('Please select a future date and time for the booking.')
        return booking_date


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your review here...', 'rows': 3}),
        }


class ServiceFilterForm(forms.Form):
    CATEGORY_CHOICES = [('', 'All Categories')]
    CITY_CHOICES = [
        ('', 'All Cities'),
        ('Ahmedabad', 'Ahmedabad'),
        ('Surat', 'Surat'),
        ('Vadodara', 'Vadodara'),
        ('Rajkot', 'Rajkot'),
        ('Gandhinagar', 'Gandhinagar'),
    ]
    EXPERIENCE_CHOICES = [
        ('', 'Any Experience'),
        ('1', '1+ Years'),
        ('3', '3+ Years'),
        ('5', '5+ Years'),
        ('10', '10+ Years'),
    ]
    SORT_CHOICES = [
        ('newest_first', 'Newest First'),
        ('oldest_first', 'Oldest First'),
        ('price_low', 'Price Low to High'),
        ('price_high', 'Price High to Low'),
        ('experience_high', 'Experience High to Low'),
        ('provider_name', 'Provider Name A-Z'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by service, provider, description or category',
            'id': 'search-input'
        })
    )
    category = forms.ChoiceField(
        required=False,
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    city = forms.ChoiceField(
        required=False,
        choices=CITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    experience = forms.ChoiceField(
        required=False,
        choices=EXPERIENCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    verified_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    available_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = Category.objects.all()
        category_options = [('', 'All Categories')] + [(category.name, category.name) for category in categories]
        self.fields['category'].choices = category_options

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        if min_price is not None and max_price is not None and min_price > max_price:
            self.add_error('max_price', 'Maximum price must be greater than or equal to minimum price.')
        return cleaned_data
