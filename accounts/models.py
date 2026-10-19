import re

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# "Bayernallee 11, 52066 Aachen" or "Bayernallee 11\n52066 Aachen" -> street / postal code / city
_ADDRESS_TEXT = re.compile(r"^(?P<street>.+?)[\s,]+(?P<postal_code>\d{5})\s+(?P<city>.+)$", re.DOTALL)


def split_address(text):
    """Split a one-text address into (street, postal_code, city). Falls back to putting everything in street."""
    text = (text or "").strip()
    match = _ADDRESS_TEXT.match(text)
    if match:
        return tuple(" ".join(match.group(part).split()) for part in ("street", "postal_code", "city"))
    return " ".join(text.split()), "", ""


class Profile(models.Model):
    """Extra customer data. Name and email live on Django's built-in User
    (first_name, last_name, email). Purchase history = user.orders (see orders app).
    The address is stored in three separate fields so each part can be validated."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    street = models.CharField("Street and house number", max_length=200, blank=True)
    postal_code = models.CharField("Postal code", max_length=5, blank=True)
    city = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def address(self):
        """Full address as text, e.g. for the shipping address of an order:
        'Bayernallee 11\\n52066 Aachen'. Empty string if no address is set."""
        second_line = " ".join(part for part in (self.postal_code, self.city) if part)
        return "\n".join(line for line in (self.street, second_line) if line)

    @address.setter
    def address(self, text):
        """Still allows profile.address = "Street 1, 12345 City" (used by orders tests and seed_demo)."""
        self.street, self.postal_code, self.city = split_address(text)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """Every new user automatically gets an empty profile."""
    if created:
        Profile.objects.create(user=instance)
