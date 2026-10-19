"""Split the single 'address' text field into street, postal_code and city.
Existing addresses are copied over, so no customer data is lost."""
import re

from django.db import migrations, models

ADDRESS_TEXT = re.compile(r"^(?P<street>.+?)[\s,]+(?P<postal_code>\d{5})\s+(?P<city>.+)$", re.DOTALL)


def split_existing_addresses(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    for profile in Profile.objects.all():
        text = (profile.address or "").strip()
        match = ADDRESS_TEXT.match(text)
        if match:
            profile.street, profile.postal_code, profile.city = (
                " ".join(match.group(part).split()) for part in ("street", "postal_code", "city")
            )
        else:
            profile.street = " ".join(text.split())[:200]
        profile.save(update_fields=["street", "postal_code", "city"])


def join_addresses(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    for profile in Profile.objects.all():
        second_line = " ".join(part for part in (profile.postal_code, profile.city) if part)
        profile.address = "\n".join(line for line in (profile.street, second_line) if line)
        profile.save(update_fields=["address"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="street",
            field=models.CharField(blank=True, max_length=200, verbose_name="Street and house number"),
        ),
        migrations.AddField(
            model_name="profile",
            name="postal_code",
            field=models.CharField(blank=True, max_length=5, verbose_name="Postal code"),
        ),
        migrations.AddField(
            model_name="profile",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(split_existing_addresses, join_addresses),
        migrations.RemoveField(
            model_name="profile",
            name="address",
        ),
    ]
