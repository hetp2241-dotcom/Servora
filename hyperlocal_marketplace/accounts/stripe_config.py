import logging
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

logger = logging.getLogger(__name__)


def get_stripe_module():
    try:
        import stripe
    except ImportError as exc:
        raise ImproperlyConfigured('Install the stripe package before enabling online payments.') from exc

    if not settings.STRIPE_SECRET_KEY:
        raise ImproperlyConfigured('STRIPE_SECRET_KEY is not configured.')

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    return stripe


def amount_to_smallest_currency_unit(amount):
    return int(amount * 100)


def create_checkout_session(request, payment):
    stripe = get_stripe_module()
    booking = payment.booking
    service = booking.service
    success_url = request.build_absolute_uri(reverse('payment_success'))
    cancel_url = request.build_absolute_uri(reverse('payment_cancel', args=[payment.id]))

    # Metadata links Stripe's asynchronous webhook event to the local booking/payment rows.
    return stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        customer_email=booking.customer.email,
        line_items=[
            {
                'price_data': {
                    'currency': settings.STRIPE_CURRENCY,
                    'product_data': {
                        'name': service.name,
                        'description': service.description[:500],
                    },
                    'unit_amount': amount_to_smallest_currency_unit(payment.amount),
                },
                'quantity': 1,
            }
        ],
        metadata={
            'booking_id': str(booking.id),
            'payment_id': str(payment.id),
        },
        payment_intent_data={
            'metadata': {
                'booking_id': str(booking.id),
                'payment_id': str(payment.id),
            }
        },
        success_url=f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}',
        cancel_url=cancel_url,
    )
