from django.contrib import admin
from .models import HelpRequest


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'resident', 'request_type', 'urgency', 'status', 'ai_summary', 'address', 'created_at')
    list_filter = ('request_type', 'urgency', 'status')
    search_fields = ('resident__username', 'description', 'ai_summary', 'address')