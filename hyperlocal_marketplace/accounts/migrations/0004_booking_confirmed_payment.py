# Generated manually for Stripe payment integration.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_booking_options_booking_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('CONFIRMED', 'Confirmed'),
                    ('ACCEPTED', 'Accepted'),
                    ('REJECTED', 'Rejected'),
                    ('COMPLETED', 'Completed'),
                ],
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_payment_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    'payment_status',
                    models.CharField(
                        choices=[
                            ('PENDING', 'Pending'),
                            ('PAID', 'Paid'),
                            ('FAILED', 'Failed'),
                            ('REFUNDED', 'Refunded'),
                        ],
                        default='PENDING',
                        max_length=20,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'booking',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='payments',
                        to='accounts.booking',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
