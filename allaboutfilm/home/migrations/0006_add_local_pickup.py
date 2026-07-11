from django.db import migrations


def add_pickup(apps, schema_editor):
    ShippingMethod = apps.get_model('home', 'ShippingMethod')
    ShippingMethod.objects.get_or_create(
        name='Local Pickup',
        defaults={'price': '0.00', 'position': 0},
    )


def remove_pickup(apps, schema_editor):
    ShippingMethod = apps.get_model('home', 'ShippingMethod')
    ShippingMethod.objects.filter(name='Local Pickup').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_seed_shipping_methods'),
    ]

    operations = [
        migrations.RunPython(add_pickup, remove_pickup),
    ]
