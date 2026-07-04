from django.contrib import admin
from .models import Warning


@admin.register(Warning)
class WarningAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'warning_type', 'level', 'community', 'is_active', 'created_at')
    list_filter = ('warning_type', 'level', 'is_active', 'community')
    search_fields = ('title', 'content', 'community')