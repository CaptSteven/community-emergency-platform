from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'phone', 'community', 'is_available', 'created_at')
    list_filter = ('role', 'is_available', 'community')
    search_fields = ('user__username', 'phone', 'community', 'address')