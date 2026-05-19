from django.db import models


class TimestampedModel(models.Model):
    """Abstract base providing created_at / updated_at on every concrete model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
