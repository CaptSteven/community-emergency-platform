from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'phone', 'community', 'skills', 'current_longitude', 'current_latitude', 'is_available', 'location_updated_at', 'created_at')
    list_filter = ('role', 'is_available', 'community')
    search_fields = ('user__username', 'phone', 'community', 'address')
    fieldsets = (
        ('基础信息', {
            'fields': ('user', 'role', 'phone', 'community', 'address', 'skills', 'is_available')
        }),
        ('实时位置', {
            'fields': ('current_longitude', 'current_latitude', 'location_updated_at'),
            'description': '用于志愿者位置热力图。百度地图展示建议使用 BD-09 坐标。'
        }),
        ('系统信息', {
            'fields': ('created_at',),
        }),
    )
    readonly_fields = ('created_at',)