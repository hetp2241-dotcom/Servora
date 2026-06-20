from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

CATEGORY_IMAGE_FILENAMES = {
    'Plumber': 'service_images/plumber.jpg',
    'Electrician': 'service_images/electrician.jpg',
    'Carpenter': 'service_images/carpenter.jpg',
    'Cleaner': 'service_images/cleaner.jpg',
    'Painter': 'service_images/painter.jpg',
    'AC Repair': 'service_images/ac_repair.jpg',
    'Appliance Repair': 'service_images/appliance_repair.jpg',
}
DEFAULT_SERVICE_IMAGE = 'service_images/service_default.jpg'


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        CUSTOMER = 'CUSTOMER', _('Customer')
        PROVIDER = 'PROVIDER', _('Service Provider')

    username = None
    email = models.EmailField(_('email address'), unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_provider(self):
        return self.role == self.Role.PROVIDER


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    icon = models.CharField(max_length=120, blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def image_filename(self):
        return CATEGORY_IMAGE_FILENAMES.get(self.name, DEFAULT_SERVICE_IMAGE)

    @property
    def image_url(self):
        """URL for the category image.

        Notes:
        - In this project category images are downloaded into MEDIA_ROOT/service_images/.
        - Some category filenames may not exist (e.g. if image download failed). In that case
          fall back to DEFAULT_SERVICE_IMAGE to avoid broken <img> tags.
        """
        filename = self.image_filename

        # If expected file is missing, fall back to default so templates never point to a 404.
        expected_path = (settings.MEDIA_ROOT / filename) if hasattr(settings, 'MEDIA_ROOT') else None
        if expected_path and not expected_path.exists():
            filename = DEFAULT_SERVICE_IMAGE

        return f"{settings.MEDIA_URL}{filename}"






class ProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    profile_picture = models.ImageField(upload_to='provider_profiles/', blank=True, null=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name or self.user.full_name

    @property
    def profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return ''

    @property
    def completion_percentage(self):
        fields = [
            self.profile_picture,
            self.full_name,
            self.phone_number,
            self.address,
            self.city,
            self.experience_years,
            self.description,
        ]
        completed = sum(1 for value in fields if value)
        return int((completed / len(fields)) * 100) if fields else 0

    @property
    def is_complete(self):
        return self.completion_percentage >= 85


class Service(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='services')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_hours = models.PositiveIntegerField(default=1, help_text='Duration in hours')
    image = models.ImageField(upload_to='service_images/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} by {self.provider.full_name}"

    @property
    def title(self):
        return self.name

    @title.setter
    def title(self, value):
        self.name = value

    @property
    def duration(self):
        return self.duration_hours

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        if self.category:
            return self.category.image_url
        return f"{settings.MEDIA_URL}{DEFAULT_SERVICE_IMAGE}"

    @duration.setter
    def duration(self, value):
        self.duration_hours = value


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')
        COMPLETED = 'COMPLETED', _('Completed')

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_as_customer')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_as_provider')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.id} - {self.customer.full_name} with {self.provider.full_name}"

    @property
    def status_badge(self):
        return {
            self.Status.PENDING: 'warning',
            self.Status.CONFIRMED: 'success',
            self.Status.ACCEPTED: 'primary',
            self.Status.REJECTED: 'danger',
            self.Status.COMPLETED: 'success',
        }.get(self.status, 'secondary')


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PAID = 'PAID', _('Paid')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    stripe_payment_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} for Booking #{self.booking_id} - {self.get_payment_status_display()}"

    @property
    def status_badge(self):
        return {
            self.Status.PENDING: 'warning',
            self.Status.PAID: 'success',
            self.Status.FAILED: 'danger',
            self.Status.REFUNDED: 'secondary',
        }.get(self.payment_status, 'secondary')


class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.full_name} to {self.receiver.full_name} at {self.timestamp}"


@receiver(post_save, sender=User)
def create_provider_profile(sender, instance, created, **kwargs):
    if created and instance.role == User.Role.PROVIDER:
        ProviderProfile.objects.create(
            user=instance,
            full_name=instance.full_name,
            phone_number=instance.phone_number,
        )


@receiver(post_migrate)
def create_default_categories(sender, **kwargs):
    if sender.name != 'hyperlocal_marketplace.accounts':
        return

    default_categories = [
        ('Plumber', 'bi-droplet', 'Quality plumbing services for homes and small businesses.'),
        ('Electrician', 'bi-lightning-charge', 'Electrical installations, repairs, and safety checks.'),
        ('Carpenter', 'bi-hammer', 'Woodworking, furniture, and carpentry services.'),
        ('Cleaner', 'bi-bucket', 'Professional cleaning for residential and commercial spaces.'),
        ('Painter', 'bi-brush', 'Interior and exterior painting services with attention to detail.'),
        ('AC Repair', 'bi-snow', 'Air conditioning maintenance, repair and installation.'),
        ('Appliance Repair', 'bi-tools', 'Repair and servicing for home appliances.'),
    ]

    for name, icon, description in default_categories:
        Category.objects.get_or_create(
            name=name,
            defaults={'icon': icon, 'description': description},
        )
