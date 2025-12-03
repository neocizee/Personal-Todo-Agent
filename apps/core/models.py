from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model for the project.
    Using a custom user model from the start is a best practice in Django.
    """
    pass
