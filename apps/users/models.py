from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    VISITOR = 'visitor', 'Visitor'
    ANALYST = 'analyst', 'Analyst'
    MANAGER = 'manager', 'Manager'
    ADMIN = 'admin', 'Admin'


class AppUser(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.ANALYST)

    @property
    def is_manager_or_admin(self):
        return self.role in {UserRole.MANAGER, UserRole.ADMIN}

    @property
    def is_visitor_or_above(self):
        return self.role in {UserRole.VISITOR, UserRole.MANAGER, UserRole.ADMIN}

    @property
    def is_admin_role(self):
        return self.role == UserRole.ADMIN
