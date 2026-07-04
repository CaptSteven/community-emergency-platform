from django.contrib import admin
from .models import VolunteerTask


@admin.register(VolunteerTask)
class VolunteerTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'help_request', 'volunteer', 'status', 'assigned_at', 'accepted_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('help_request__description', 'volunteer__username', 'feedback')