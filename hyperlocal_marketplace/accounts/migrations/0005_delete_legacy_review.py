from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0003_copy_legacy_account_reviews'),
        ('accounts', '0004_booking_confirmed_payment'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Review',
        ),
    ]
