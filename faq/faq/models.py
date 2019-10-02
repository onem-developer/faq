from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

from .validators import UsernameValidator


class Faq(models.Model):
    category = models.CharField(max_length=50, blank=True, null=True)
    question = models.CharField(max_length=150, blank=True)
    answer = models.CharField(max_length=300, blank=True)

    def get_absolute_url(self):
        return reverse('faq', args=(self.id,))
