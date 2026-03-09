from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import AppUser


@admin.register(AppUser)
class AppUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role Access', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
