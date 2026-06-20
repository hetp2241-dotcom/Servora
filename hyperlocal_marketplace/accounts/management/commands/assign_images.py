import os
import random
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.files import File
from django.db import transaction

from hyperlocal_marketplace.accounts.models import Category, ProviderProfile, Service, User

PROFILE_IMAGES = [
    'https://images.pexels.com/photos/1181699/pexels-photo-1181699.jpeg',
    'https://images.pexels.com/photos/1181359/pexels-photo-1181359.jpeg',
    'https://images.pexels.com/photos/1181356/pexels-photo-1181356.jpeg',
    'https://images.pexels.com/photos/220453/pexels-photo-220453.jpeg',
    'https://images.pexels.com/photos/3771097/pexels-photo-3771097.jpeg',
    'https://images.pexels.com/photos/3762808/pexels-photo-3762808.jpeg',
    'https://images.pexels.com/photos/3771045/pexels-photo-3771045.jpeg',
    'https://images.pexels.com/photos/3760857/pexels-photo-3760857.jpeg',
    'https://images.pexels.com/photos/3875521/pexels-photo-3875521.jpeg',
    'https://images.pexels.com/photos/3748221/pexels-photo-3748221.jpeg',
]

CATEGORY_IMAGES = {
    'Plumber': 'https://images.pexels.com/photos/5450114/pexels-photo-5450114.jpeg',
    'Electrician': 'https://images.pexels.com/photos/1020311/pexels-photo-1020311.jpeg',
    'Carpenter': 'https://images.pexels.com/photos/7578801/pexels-photo-7578801.jpeg',
    'Cleaner': 'https://images.pexels.com/photos/4491463/pexels-photo-4491463.jpeg',
    'Painter': 'https://images.pexels.com/photos/3326459/pexels-photo-3326459.jpeg',
    'AC Repair': 'https://images.pexels.com/photos/5058935/pexels-photo-5058935.jpeg',
    'Appliance Repair': 'https://images.pexels.com/photos/4566685/pexels-photo-4566685.jpeg',
}

SERVICE_IMAGE_MAP = {
    'Plumber': 'plumber.jpg',
    'Electrician': 'electrician.jpg',
    'Carpenter': 'carpenter.jpg',
    'Cleaner': 'cleaner.jpg',
    'Painter': 'painter.jpg',
    'AC Repair': 'ac_repair.jpg',
    'Appliance Repair': 'appliance_repair.jpg',
}


class Command(BaseCommand):
    help = 'Assign realistic provider avatars and service category images for all existing records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reassign images even if providers or services already have images.',
        )

    def handle(self, *args, **options):
        self.media_root = Path(settings.MEDIA_ROOT)
        self.provider_dir = self.media_root / 'provider_profiles'
        self.service_dir = self.media_root / 'service_images'
        self.provider_dir.mkdir(parents=True, exist_ok=True)
        self.service_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS('Media directories verified.'))
        self.download_category_images()
        self.assign_provider_profile_images(force=options['force'])
        self.assign_service_category_images(force=options['force'])

    def download_category_images(self):
        self.stdout.write('Downloading category images...')
        for category_name, url in CATEGORY_IMAGES.items():
            local_name = SERVICE_IMAGE_MAP.get(category_name)
            if not local_name:
                continue
            destination = self.service_dir / local_name
            if destination.exists():
                self.stdout.write(f'  Skipping existing category image: {local_name}')
                continue
            self.download_image(url, destination)
            self.stdout.write(f'  Saved category image: {category_name} -> {destination.name}')

    def assign_provider_profile_images(self, force=False):
        provider_profiles = ProviderProfile.objects.select_related('user')
        self.stdout.write(f'Assigning profile images for {provider_profiles.count()} providers...')
        image_urls = PROFILE_IMAGES.copy()
        random.shuffle(image_urls)

        for idx, profile in enumerate(provider_profiles, start=1):
            if profile.profile_picture and not force:
                self.stdout.write(f'  Skipping existing profile image for {profile.full_name}')
                continue

            image_url = image_urls[(idx - 1) % len(image_urls)]
            filename = f"provider_{profile.user.id}_{profile.user.full_name.replace(' ', '_').lower()}.jpg"
            local_path = self.provider_dir / filename
            self.download_image(image_url, local_path)
            self.save_profile_picture(profile, local_path)
            self.stdout.write(f'  Assigned avatar for {profile.full_name}')

    def assign_service_category_images(self, force=False):
        services = Service.objects.select_related('category', 'provider__provider_profile')
        self.stdout.write(f'Assigning service images for {services.count()} services...')

        for service in services:
            category_name = service.category.name if service.category else None
            if not category_name or category_name not in SERVICE_IMAGE_MAP:
                self.stdout.write(f'  Skipping service without mapped category: {service.name}')
                continue

            if service.image and not force:
                self.stdout.write(f'  Skipping existing image for service {service.name}')
                continue

            category_filename = SERVICE_IMAGE_MAP[category_name]
            source_path = self.service_dir / category_filename
            if not source_path.exists():
                self.stdout.write(self.style.ERROR(f'  Missing category image file for {category_name}: {category_filename}'))
                continue

            self.save_service_image(service, source_path)
            self.stdout.write(f'  Assigned {category_name} image to service {service.name}')

    def download_image(self, url, destination: Path):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()

            destination.write_bytes(content)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'    Failed to download {url}: {exc}'))

    def save_profile_picture(self, profile: ProviderProfile, path: Path):
        with path.open('rb') as image_file:
            profile.profile_picture.save(path.name, File(image_file), save=False)
            profile.save()

    def save_service_image(self, service: Service, path: Path):
        with path.open('rb') as image_file:
            service.image.save(path.name, File(image_file), save=False)
            service.save()
