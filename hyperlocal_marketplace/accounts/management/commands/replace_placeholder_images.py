import os
import re
import sys
import hashlib
import random
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.files import File
from django.db import transaction
from PIL import Image

from hyperlocal_marketplace.accounts.models import ProviderProfile, Service


@dataclass(frozen=True)
class ImageAsset:
    path: Path
    sha256: str


def normalize_category_name_to_slug(name: str) -> str:
    if not name:
        return ''

    slug = name.strip().lower()
    slug = slug.replace('&', 'and')
    slug = slug.replace(' ', '-')
    # remove unsupported characters, keep alnum and hyphen
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')
    return slug


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_image_files(folder: Path):
    if not folder.exists() or not folder.is_dir():
        return
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
            yield p


def process_image_to_jpeg_bytes(
    src_path: Path,
    *,
    target_max_w: int,
    target_max_h: int,
    quality: int = 85,
    progressive: bool = True,
):
    # Read + process via Pillow
    with Image.open(src_path) as im:
        im = im.convert('RGB')

        # Resize keeping aspect ratio
        w, h = im.size
        scale = min(target_max_w / w, target_max_h / h, 1.0)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        if (new_w, new_h) != (w, h):
            im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Encode to JPEG in-memory
        from io import BytesIO

        buf = BytesIO()
        im.save(
            buf,
            format='JPEG',
            quality=quality,
            optimize=True,
            progressive=progressive,
        )
        return buf.getvalue()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = (
        'Replaces placeholder/provider/service images using local candidate assets, '
        'resizing/optimizing, deduping by hash, and updating ProviderProfile.profile_picture '
        'and Service.image.'
    )

    def _log(self, msg: str):
        self.stdout.write(msg)
        # ensure logs flush even when stdout is buffered
        try:
            self.stdout.flush()
        except Exception:
            pass

    def add_arguments(self, parser):

        parser.add_argument(
            '--assets-root',
            type=str,
            default='assets',
            help='Root folder containing provider_headshots/ and service_images/.',
        )
        parser.add_argument(
            '--provider-count',
            type=int,
            default=50,
            help='Target number of unique provider images to assign (defaults to 50).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='If set, reassign images even if ProviderProfile.profile_picture or Service.image already exist.',
        )

    def handle(self, *args, **options):
        self._log('COMMAND START: replace_placeholder_images')
        self._log(f"COMMAND ARGS: assets_root={options.get('assets_root')} provider_count={options.get('provider_count')} force={options.get('force')}")
        assets_root = Path(options['assets_root']).resolve()

        provider_count_target = int(options['provider_count'])
        force = bool(options['force'])

        if not assets_root.exists():
            raise SystemExit(f'ERROR: assets root folder does not exist: {assets_root}')

        provider_candidates_dir = assets_root / 'provider_headshots'
        service_candidates_root = assets_root / 'service_images'
        self._log(f"ASSET FOLDERS: provider_candidates_dir={provider_candidates_dir} exists={provider_candidates_dir.exists()} is_dir={provider_candidates_dir.is_dir()} ; service_candidates_root={service_candidates_root} exists={service_candidates_root.exists()} is_dir={service_candidates_root.is_dir()}")


        provider_out_dir = Path(settings.MEDIA_ROOT) / 'provider_profiles'
        service_out_dir = Path(settings.MEDIA_ROOT) / 'service_images'
        provider_out_dir.mkdir(parents=True, exist_ok=True)
        service_out_dir.mkdir(parents=True, exist_ok=True)

        provider_profiles = list(
            ProviderProfile.objects.select_related('user').all().order_by('id')
        )
        services = list(
            Service.objects.select_related('category').all().order_by('id')
        )

        providers_needing = [
            p for p in provider_profiles if (force or not p.profile_picture)
        ]
        services_needing = [
            s for s in services if (force or not s.image)
        ]

        if not provider_candidates_dir.exists():
            raise SystemExit(
                f'ERROR: missing provider candidates folder: {provider_candidates_dir}'
            )

        provider_candidate_images = [
            p for p in iter_image_files(provider_candidates_dir)
        ]
        if len(provider_candidate_images) < provider_count_target:
            raise SystemExit(
                f'ERROR: not enough provider candidate images. '
                f'Need at least {provider_count_target}, found {len(provider_candidate_images)} in {provider_candidates_dir}'
            )

        # Service candidates folder checks are per-category (as per requirements)

        self.stdout.write('--- replace_placeholder_images ---')
        self.stdout.write(f'Assets root: {assets_root}')
        self.stdout.write(f'Providers in DB: {len(provider_profiles)}; needing update: {len(providers_needing)}')
        self.stdout.write(f'Services in DB: {len(services)}; needing update: {len(services_needing)}')

        # Provider assignment pool + dedupe
        provider_unique_assets = []
        seen_provider_hashes = set()
        skipped_provider_images = 0

        # Shuffle to avoid deterministic ordering bias
        random.shuffle(provider_candidate_images)

        for src in provider_candidate_images:
            if len(provider_unique_assets) >= provider_count_target:
                break

            try:
                jpeg_bytes = process_image_to_jpeg_bytes(
                    src,
                    target_max_w=512,
                    target_max_h=512,
                    quality=85,
                    progressive=True,
                )
                h = sha256_bytes(jpeg_bytes)
            except Exception as exc:
                skipped_provider_images += 1
                self.stdout.write(self.style.WARNING(f'  Skipping provider image (process error): {src.name} ({exc})'))
                continue

            if h in seen_provider_hashes:
                skipped_provider_images += 1
                continue

            seen_provider_hashes.add(h)
            provider_unique_assets.append(ImageAsset(path=src, sha256=h))

        if len(provider_unique_assets) < min(provider_count_target, len(providers_needing)):
            raise SystemExit(
                f'ERROR: could not assemble enough unique provider images. '
                f'Unique processed providers available: {len(provider_unique_assets)}; '
                f'Providers needing update: {len(providers_needing)}; '
                f'Target provider-count: {provider_count_target}'
            )

        # Prepare mapping: provider -> chosen asset index (unique)
        random.shuffle(provider_unique_assets)
        provider_assignment = {}
        for i, profile in enumerate(providers_needing):
            asset = provider_unique_assets[i % len(provider_unique_assets)]
            provider_assignment[profile.id] = asset

        # Service assignment pool per category + dedupe
        services_updated = 0
        providers_updated = 0
        duplicate_images_removed = 0  # dedupe across all processed candidates for assignments

        # Deduplication stats: we will count duplicates within candidate processing per category/provider
        # by comparing candidate hashes to seen.

        # Cache: category slug -> list[ImageAsset]
        service_assets_by_slug = {}
        service_seen_hashes_by_slug = {}
        skipped_service_images = 0
        missing_category_folders = []

        # Precompute which category slugs we need (only for services needing update)
        required_slugs = set()
        for s in services_needing:
            if not s.category:
                continue
            required_slugs.add(normalize_category_name_to_slug(s.category.name))

        # For each required slug, build unique processed assets list from local candidate folder
        for slug in sorted(required_slugs):
            folder = service_candidates_root / slug
            if not folder.exists():
                missing_category_folders.append(slug)
                continue

            candidate_files = list(iter_image_files(folder))
            if not candidate_files:
                missing_category_folders.append(slug)
                continue

            random.shuffle(candidate_files)

            assets = []
            seen = set()
            duplicates_within_candidates = 0

            for src in candidate_files:
                try:
                    jpeg_bytes = process_image_to_jpeg_bytes(
                        src,
                        target_max_w=1200,
                        target_max_h=800,
                        quality=85,
                        progressive=True,
                    )
                    h = sha256_bytes(jpeg_bytes)
                except Exception as exc:
                    skipped_service_images += 1
                    self.stdout.write(self.style.WARNING(f'  Skipping service image (process error): {src.name} ({exc})'))
                    continue

                if h in seen:
                    duplicates_within_candidates += 1
                    continue

                seen.add(h)
                assets.append(ImageAsset(path=src, sha256=h))

            duplicate_images_removed += duplicates_within_candidates
            service_assets_by_slug[slug] = assets
            service_seen_hashes_by_slug[slug] = seen

        # Now assign unique images per service needing update
        service_assignment = {}
        for s in services_needing:
            if not s.category:
                continue
            slug = normalize_category_name_to_slug(s.category.name)
            assets = service_assets_by_slug.get(slug)
            if not assets:
                # Missing folder or no usable images
                continue

            # Assign deterministically but unique by consuming a shuffled list
            # We do it by counting already-assigned per slug.
            assigned_count = service_assignment.get(('__count__', slug), 0)
            # store count in tuple key
            service_assignment[('___count___', slug)] = assigned_count

        # Second pass with proper consumption
        per_slug_next_index = {slug: 0 for slug in service_assets_by_slug.keys()}
        for s in services_needing:
            if not s.category:
                continue
            slug = normalize_category_name_to_slug(s.category.name)
            assets = service_assets_by_slug.get(slug)
            if not assets:
                continue

            idx = per_slug_next_index.get(slug, 0)
            if idx >= len(assets):
                # ran out; skip further services for that slug
                continue

            service_assignment[s.id] = assets[idx]
            per_slug_next_index[slug] = idx + 1

        # Write image files + update DB
        files_updated = []
        missing_provider_images = []
        images_skipped = 0

        with transaction.atomic():
            # Providers
            for profile in providers_needing:
                asset = provider_assignment.get(profile.id)
                if not asset:
                    missing_provider_images.append(profile.id)
                    continue

                try:
                    jpeg_bytes = process_image_to_jpeg_bytes(
                        asset.path,
                        target_max_w=512,
                        target_max_h=512,
                        quality=85,
                        progressive=True,
                    )
                    h = sha256_bytes(jpeg_bytes)
                except Exception as exc:
                    images_skipped += 1
                    self.stdout.write(self.style.WARNING(f'  Skipping provider id={profile.id} (reprocess error): {exc}'))
                    continue

                out_name = f'provider_{profile.user_id}_{h[:12]}.jpg'
                out_path = provider_out_dir / out_name
                if not out_path.exists():
                    out_path.write_bytes(jpeg_bytes)
                    files_updated.append(str(out_path.relative_to(settings.MEDIA_ROOT)))

                with out_path.open('rb') as f:
                    profile.profile_picture.save(out_path.name, File(f), save=False)
                profile.save()
                providers_updated += 1

            # Services
            for s in services_needing:
                asset = service_assignment.get(s.id)
                if not asset:
                    continue

                try:
                    jpeg_bytes = process_image_to_jpeg_bytes(
                        asset.path,
                        target_max_w=1200,
                        target_max_h=800,
                        quality=85,
                        progressive=True,
                    )
                    h = sha256_bytes(jpeg_bytes)
                except Exception as exc:
                    images_skipped += 1
                    self.stdout.write(self.style.WARNING(f'  Skipping service id={s.id} (reprocess error): {exc}'))
                    continue

                out_name = f'service_{s.id}_{h[:12]}.jpg'
                out_path = service_out_dir / out_name
                if not out_path.exists():
                    out_path.write_bytes(jpeg_bytes)
                    files_updated.append(str(out_path.relative_to(settings.MEDIA_ROOT)))

                with out_path.open('rb') as f:
                    s.image.save(out_path.name, File(f), save=False)
                s.save()
                services_updated += 1

        # Final verification: compute hashes of referenced images and ensure uniqueness
        referenced_provider_hashes = []
        for p in ProviderProfile.objects.select_related('user').all():
            if p.profile_picture and p.profile_picture.name:
                img_path = Path(settings.MEDIA_ROOT) / p.profile_picture.name
                if img_path.exists():
                    referenced_provider_hashes.append(file_sha256(img_path))

        referenced_service_hashes = []
        for s in Service.objects.select_related('category').all():
            if s.image and s.image.name:
                img_path = Path(settings.MEDIA_ROOT) / s.image.name
                if img_path.exists():
                    referenced_service_hashes.append(file_sha256(img_path))

        all_hashes = referenced_provider_hashes + referenced_service_hashes
        dup_hashes = {}
        for h in all_hashes:
            dup_hashes[h] = dup_hashes.get(h, 0) + 1
        duplicate_refs = {h: c for h, c in dup_hashes.items() if c > 1}

        # Deduce “duplicate images removed” more strictly from assignments is complex; we already tracked duplicates-within-candidates.
        # What matters for requirement is verification.

        # Compute counts of unique referenced files
        unique_provider_hashes = set(referenced_provider_hashes)
        unique_service_hashes = set(referenced_service_hashes)

        self.stdout.write('--- Report ---')
        self.stdout.write(f'Providers updated: {providers_updated}')
        self.stdout.write(f'Services updated: {services_updated}')
        self.stdout.write(f'Duplicate images removed (candidate dedupe count): {duplicate_images_removed}')
        self.stdout.write(f'Missing category folders (for services): {missing_category_folders}')
        self.stdout.write(f'Missing provider images (provider profile IDs): {missing_provider_images}')
        self.stdout.write(f'Images skipped (processing failures / unassigned): {images_skipped}')
        self.stdout.write(f'Final unique provider image count (referenced): {len(unique_provider_hashes)}')
        self.stdout.write(f'Final unique service image count (referenced): {len(unique_service_hashes)}')

        if duplicate_refs:
            self.stdout.write(self.style.ERROR('Verification FAILED: duplicate image hashes are referenced by the database.'))
            # show up to a few offenders
            offenders = list(duplicate_refs.items())[:10]
            for h, c in offenders:
                self.stdout.write(f'  hash={h[:24]}... count={c}')
            raise SystemExit(1)
        else:
            self.stdout.write(self.style.SUCCESS('Verification PASSED: no duplicate image hashes are referenced by the database.'))

        self.stdout.write(f'Files updated (newly written into media): {len(files_updated)}')
        for rel in files_updated[:50]:
            self.stdout.write(f'  {rel}')
        if len(files_updated) > 50:
            self.stdout.write(f'  ... and {len(files_updated) - 50} more')

