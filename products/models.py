from django.db import models


class Product(models.Model):
    """A book in the shop. Required by the lab: name, description, price."""

    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    cover_url = models.URLField("Cover image URL", blank=True)  # link to a cover image online
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
