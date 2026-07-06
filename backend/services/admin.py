from django.contrib import admin

from .models import ServiceType, ServiceSubscription, ServiceVisit


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'required_skill', 'default_frequency', 'is_active')
    list_filter = ('is_active', 'default_frequency', 'category')
    search_fields = ('name', 'code', 'category')


@admin.register(ServiceSubscription)
class ServiceSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('resident', 'service_type', 'frequency', 'is_active', 'last_generated_date')
    list_filter = ('is_active', 'frequency', 'service_type')
    search_fields = ('resident__username', 'address')


@admin.register(ServiceVisit)
class ServiceVisitAdmin(admin.ModelAdmin):
    list_display = ('resident', 'service_type', 'volunteer', 'scheduled_date', 'status')
    list_filter = ('status', 'service_type', 'scheduled_date')
    search_fields = ('resident__username', 'volunteer__username')
