from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from .models import Service, Booking

User = get_user_model()

class CustomUserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            full_name='John Customer',
            phone_number='1234567890',
            role=User.Role.CUSTOMER
        )
        self.assertEqual(user.email, 'customer@example.com')
        self.assertTrue(user.check_password('password123'))
        self.assertEqual(user.full_name, 'John Customer')
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_customer)
        self.assertFalse(user.is_provider)
        self.assertFalse(user.is_admin)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            full_name='Admin Owner'
        )
        self.assertEqual(admin.email, 'admin@example.com')
        self.assertTrue(admin.check_password('password123'))
        self.assertEqual(admin.full_name, 'Admin Owner')
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_admin)


class AuthenticationViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            full_name='John Customer',
            role=User.Role.CUSTOMER
        )
        self.provider = User.objects.create_user(
            email='provider@example.com',
            password='password123',
            full_name='Jane Provider',
            role=User.Role.PROVIDER
        )
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            full_name='Super Admin'
        )

    def test_login_redirect_customer(self):
        response = self.client.post(reverse('login'), {
            'username': 'customer@example.com',
            'password': 'password123',
        }, follow=True)
        self.assertRedirects(response, reverse('customer_dashboard'))

    def test_login_redirect_provider(self):
        response = self.client.post(reverse('login'), {
            'username': 'provider@example.com',
            'password': 'password123',
        }, follow=True)
        self.assertRedirects(response, reverse('provider_dashboard'))

    def test_login_redirect_admin(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin@example.com',
            'password': 'password123',
        }, follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_login_failure(self):
        response = self.client.post(reverse('login'), {
            'username': 'customer@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200) # Re-renders login
        self.assertTemplateUsed(response, 'accounts/login.html')
        
        # Verify message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid email or password" in str(m) for m in messages))

    def test_registration_success(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'New Customer',
            'email': 'newcustomer@example.com',
            'phone_number': '9999999999',
            'password1': 'password123!',
            'password2': 'password123!',
            'role': 'CUSTOMER'
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(email='newcustomer@example.com').exists())
        user = User.objects.get(email='newcustomer@example.com')
        self.assertEqual(user.role, User.Role.CUSTOMER)


class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(
            email='customer@example.com',
            password='password123',
            full_name='John Customer',
            role=User.Role.CUSTOMER
        )
        self.provider = User.objects.create_user(
            email='provider@example.com',
            password='password123',
            full_name='Jane Provider',
            role=User.Role.PROVIDER
        )

    def test_customer_accessing_provider_dashboard_redirected(self):
        # Log in as customer
        self.client.login(email='customer@example.com', password='password123')
        
        # Try to access provider dashboard
        response = self.client.get(reverse('provider_dashboard'))
        
        # Must redirect customer to customer_dashboard with error
        self.assertRedirects(response, reverse('customer_dashboard'))
        
        # Verify error message is present
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Access Denied" in str(m) for m in messages))

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse('customer_dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('customer_dashboard')}")
