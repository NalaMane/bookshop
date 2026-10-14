from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Extra customer data. Name and email live on Django's built-in User
    (first_name, last_name, email). Purchase history = user.orders (see orders app)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    address = models.TextField(blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """Every new user automatically gets an empty profile."""
    if created:
        Profile.objects.create(user=instance)
