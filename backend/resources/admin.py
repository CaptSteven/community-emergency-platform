from django.contrib import admin
from .models import Shelter, Material


@admin.register(Shelter)
class ShelterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'capacity', 'contact_phone', 'is_available')
    list_filter = ('is_available',)
    search_fields = ('name', 'address', 'contact_phone')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'quantity', 'unit', 'storage_location', 'warning_quantity', 'expire_date', 'expiry_warning_days', 'updated_at')
    list_filter = ('category', 'expire_date')
    search_fields = ('name', 'category', 'storage_location')