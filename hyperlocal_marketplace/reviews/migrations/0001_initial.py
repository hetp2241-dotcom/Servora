# Generated manually for the reviews app.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0004_booking_confirmed_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProviderRatingStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('average_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('review_count', models.PositiveIntegerField(default=0)),
                ('five_star_count', models.PositiveIntegerField(default=0)),
                ('four_star_count', models.PositiveIntegerField(default=0)),
                ('three_star_count', models.PositiveIntegerField(default=0)),
                ('two_star_count', models.PositiveIntegerField(default=0)),
                ('one_star_count', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rating_stats', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'provider rating stats',
            },
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])),
                ('comment', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_review', to='accounts.booking')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_reviews_written', to=settings.AUTH_USER_MODEL)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_reviews_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['provider', '-created_at'], name='reviews_rev_provide_75377a_idx'),
                    models.Index(fields=['customer', '-created_at'], name='reviews_rev_custome_6d90f0_idx'),
                    models.Index(fields=['rating'], name='reviews_rev_rating_9c5446_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('booking',), name='unique_review_per_booking'),
                ],
            },
        ),
    ]
