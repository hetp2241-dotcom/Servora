from decimal import Decimal
from datetime import timedelta
import random
from django.utils import timezone

from hyperlocal_marketplace.accounts.models import (
    User,
    Category,
    ProviderProfile,
    Service,
    Booking,
)

from hyperlocal_marketplace.reviews.models import Review


PROVIDER_CITY_CHOICES = [
    'Ahmedabad',
    'Surat',
    'Vadodara',
    'Rajkot',
    'Gandhinagar',
]

CATEGORY_DATA = {
    'Plumber': [
        'Pipe Leak Repair',
        'Bathroom Fitting',
        'Water Tank Installation',
        'Drain Cleaning Service',
        'Tap & Faucet Repair',
    ],
    'Electrician': [
        'Fan Installation',
        'Wiring Repair',
        'Switch Board Repair',
        'Light Fixture Installation',
        'Electrical Safety Inspection',
    ],
    'Carpenter': [
        'Furniture Repair',
        'Door Installation',
        'Modular Furniture Assembly',
        'Wooden Shelf Installation',
        'Cupboard Repair',
    ],
    'Cleaner': [
        'Home Cleaning',
        'Kitchen Deep Cleaning',
        'Bathroom Cleaning',
        'Sofa Cleaning',
        'Carpet Cleaning',
    ],
    'Painter': [
        'Interior Painting',
        'Exterior Painting',
        'Texture Painting',
        'Wall Repair & Painting',
        'Woodwork Painting',
    ],
    'AC Repair': [
        'AC Service',
        'AC Installation',
        'AC Gas Refill',
        'AC Filter Cleaning',
        'AC Compressor Repair',
    ],
    'Appliance Repair': [
        'Washing Machine Repair',
        'Refrigerator Repair',
        'Microwave Repair',
        'Dishwasher Repair',
        'Geyser Repair',
    ],
}

PROVIDER_DESCRIPTIONS = [
    'Experienced professional with a focus on fast, reliable service.',
    'Trusted local provider offering affordable rates and quality workmanship.',
    'Customer-first handyman with strong reviews for prompt service.',
    'Dedicated to delivering safe, clean, and dependable solutions.',
    'Skilled specialist with years of hands-on experience in this domain.',
]

REVIEW_COMMENTS = [
    'Completed the job quickly and neatly. Very satisfied with the service.',
    'Professional attitude and good communication throughout.',
    'The service quality was excellent and the pricing was fair.',
    'Problem fixed on the first visit with good attention to detail.',
    'Friendly technician who arrived on time and completed the work efficiently.',
    'Highly recommended for anyone looking for trusted home services.',
    'Service was prompt and the repair lasted well after completion.',
    'They were careful with my home and cleaned up after the job.',
    'Very responsive and easy to book. The work quality is solid.',
    'Good service overall, would hire again for future maintenance.',
]

INDIAN_FIRST_NAMES = [
    'Aarav', 'Aditya', 'Arjun', 'Dev', 'Ishaan', 'Kabir', 'Karan', 'Mohit', 'Rohan', 'Sahil',
    'Ananya', 'Isha', 'Riya', 'Saanvi', 'Priya', 'Neha', 'Kavya', 'Meera', 'Anika', 'Pooja',
]

INDIAN_LAST_NAMES = [
    'Patel', 'Shah', 'Mehta', 'Singh', 'Joshi', 'Desai', 'Agarwal', 'Kumar', 'Gupta', 'Reddy',
    'Chopra', 'Malhotra', 'Sharma', 'Nair', 'Iyer', 'Das', 'Ghosh', 'Saxena', 'Mukherjee', 'Joshi',
]

ADDRESS_TEMPLATES = [
    'Flat {flat}, {street}, {area}',
    '{floor} Floor, {street}, {area}',
    '{house} {street}, {area}',
    '{flat}/{floor}, {street}, {area}',
]

STREETS = [
    'MG Road', 'Satellite Road', 'SG Highway', 'Ring Road', 'Airport Road',
    'Friends Colony', 'Civil Nagar', 'Shastri Marg', 'Ashram Road', 'Nehru Road',
]

AREAS = [
    'Navrangpura', 'Vastrapur', 'Maninagar', 'Paldi', 'Vijaynagar',
    'Bhayli', 'Waghodia', 'Memnagar', 'Katargam', 'Rajmahel',
]

BOOKING_STATUSES = ['PENDING', 'ACCEPTED', 'REJECTED', 'COMPLETED']


def unique_email(base, index, domain='example.com'):
    username = base.lower().replace(' ', '.')
    return f'{username}.{index}@{domain}'


def make_address():
    template = random.choice(ADDRESS_TEMPLATES)
    return template.format(
        flat=random.randint(101, 405),
        floor=random.randint(1, 6),
        house=random.randint(12, 225),
        street=random.choice(STREETS),
        area=random.choice(AREAS),
    )


def make_provider_description():
    return random.choice(PROVIDER_DESCRIPTIONS)


def make_ahmedabad_latitude():
    return round(random.uniform(23.000000, 23.100000), 6)


def make_ahmedabad_longitude():
    return round(random.uniform(72.500000, 72.700000), 6)



def make_service_description(service_name, category_name):
    return f'{service_name} by a verified {category_name.lower()} specialist. Reliable service with transparent pricing and a satisfaction guarantee.'


def make_booking_date():
    now = timezone.now()
    delta_days = random.randint(-20, 20)
    delta_hours = random.randint(1, 8)
    return now + timedelta(days=delta_days, hours=delta_hours)


def make_rating():
    return random.randint(3, 5)


def seed_categories():
    print('Seeding categories...')
    categories = {}
    for name, service_names in CATEGORY_DATA.items():
        category, created = Category.objects.get_or_create(
            name=name,
            defaults={
                'icon': '',
                'description': f'{name} services for homes and businesses.',
            },
        )
        categories[name] = category
    return categories


def seed_providers(count=50):
    print(f'Seeding {count} provider users...')
    providers = []
    available_names = [f'{first} {last}' for first in INDIAN_FIRST_NAMES for last in INDIAN_LAST_NAMES]
    random.shuffle(available_names)

    for idx in range(count):
        full_name = available_names[idx]
        email = unique_email(full_name, idx + 1, 'provider.example.com')
        phone_number = f'+91{random.randint(6000000000, 9999999999)}'

        provider, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'phone_number': phone_number,
                'role': User.Role.PROVIDER,
                'is_active': True,
            },
        )
        if created:
            provider.set_password('provider123')
            provider.save()

        # Ensure realistic Ahmedabad coordinates (not identical for all providers)
        default_lat = make_ahmedabad_latitude()
        default_lng = make_ahmedabad_longitude()

        profile, _ = ProviderProfile.objects.get_or_create(
            user=provider,
            defaults={
                'full_name': provider.full_name,
                'phone_number': provider.phone_number,
                'city': 'Ahmedabad',
                'address': make_address(),
                'latitude': default_lat,
                'longitude': default_lng,
                'experience_years': random.randint(1, 15),
                'description': make_provider_description(),
                'is_verified': True,
            },
        )

        # Always refresh coordinates so older seed runs get proper randomized Ahmedabad values.
        # Do NOT overwrite address if it already exists.
        profile.city = profile.city or 'Ahmedabad'
        profile.address = profile.address or make_address()
        profile.latitude = default_lat
        profile.longitude = default_lng

        profile.experience_years = profile.experience_years or random.randint(1, 15)
        profile.description = profile.description or make_provider_description()
        profile.is_verified = True
        profile.save()


        providers.append(provider)
    return providers


def seed_customers(count=30):
    print(f'Seeding {count} customer users...')
    customers = []
    remaining_names = [f'{first} {last}' for first in INDIAN_FIRST_NAMES for last in INDIAN_LAST_NAMES]
    random.shuffle(remaining_names)

    for idx in range(count):
        full_name = remaining_names[idx + 60]
        email = unique_email(full_name, idx + 1, 'customer.example.com')
        phone_number = f'+91{random.randint(6000000000, 9999999999)}'

        customer, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'phone_number': phone_number,
                'role': User.Role.CUSTOMER,
                'is_active': True,
            },
        )
        if created:
            customer.set_password('customer123')
            customer.save()

        customers.append(customer)
    return customers


def seed_services(providers, categories, target_count=100):
    print(f'Seeding {target_count} services...')
    created_services = []
    attempts = 0
    while len(created_services) < target_count and attempts < target_count * 4:
        provider = random.choice(providers)
        category_name = random.choice(list(CATEGORY_DATA.keys()))
        category = categories[category_name]
        service_name = random.choice(CATEGORY_DATA[category_name])
        description = make_service_description(service_name, category_name)
        price = Decimal(random.randint(199, 2999))
        duration_hours = random.randint(1, 8)

        service, created = Service.objects.get_or_create(
            provider=provider,
            category=category,
            name=service_name,
            defaults={
                'description': description,
                'price': price,
                'duration_hours': duration_hours,
                'is_available': True,
            },
        )
        if created:
            created_services.append(service)
        else:
            service.description = description
            service.price = price
            service.duration_hours = duration_hours
            service.is_available = True
            service.save()
        attempts += 1

    if len(created_services) < target_count:
        print(f'Warning: created only {len(created_services)} unique services after {attempts} attempts.')

    return Service.objects.filter(is_available=True)


def seed_bookings(customers, services, target_count=50):
    print(f'Seeding {target_count} bookings...')
    booking_records = []
    for _ in range(target_count):
        service = random.choice(list(services))
        customer = random.choice(customers)
        booking_date = make_booking_date()
        status = random.choices(
            BOOKING_STATUSES,
            weights=[25, 30, 20, 25],
            k=1,
        )[0]

        booking, created = Booking.objects.get_or_create(
            customer=customer,
            service=service,
            booking_date=booking_date,
            defaults={
                'provider': service.provider,
                'status': status,
            },
        )
        if created:
            booking_records.append(booking)
        else:
            booking.status = status
            booking.provider = service.provider
            booking.save()
            booking_records.append(booking)
    return booking_records


def seed_reviews(bookings, target_count=30):
    print(f'Seeding {target_count} reviews...')
    eligible_bookings = [b for b in bookings if b.status in ('ACCEPTED', 'COMPLETED')]
    if len(eligible_bookings) < target_count:
        eligible_bookings = Booking.objects.filter(status__in=['ACCEPTED', 'COMPLETED'])

    selected_bookings = random.sample(list(eligible_bookings), min(target_count, len(eligible_bookings)))
    reviews = []
    for idx, booking in enumerate(selected_bookings):
        rating = make_rating()
        comment = random.choice(REVIEW_COMMENTS)

        review, created = Review.objects.get_or_create(
            booking=booking,
            defaults={
                'customer': booking.customer,
                'provider': booking.provider,
                'rating': rating,
                'comment': comment,
            },
        )
        if not created:
            review.rating = rating
            review.comment = comment
            review.save()
        reviews.append(review)
    return reviews


def run_seed():
    print('Starting seed process for Hyperlocal Service Marketplace...')
    categories = seed_categories()
    providers = seed_providers(count=50)
    customers = seed_customers(count=30)
    services = seed_services(providers, categories, target_count=100)
    bookings = seed_bookings(customers, services, target_count=50)
    reviews = seed_reviews(bookings, target_count=30)

    print('\nSeed summary:')
    print(f'Providers: {len(providers)}')
    print(f'Customers: {len(customers)}')
    print(f'Services: {services.count()}')
    print(f'Bookings: {len(bookings)}')
    print(f'Reviews: {len(reviews)}')


if __name__ == '__main__':
    run_seed()
