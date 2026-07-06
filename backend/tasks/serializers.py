from rest_framework import serializers
from .models import VolunteerTask


class VolunteerTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    volunteer_name = serializers.CharField(source='volunteer.username', read_only=True)
    help_request_description = serializers.CharField(source='help_request.description', read_only=True)
    help_request_type = serializers.CharField(source='help_request.get_request_type_display', read_only=True)
    help_request_address = serializers.CharField(source='help_request.address', read_only=True)
    help_request_latitude = serializers.DecimalField(source='help_request.latitude', max_digits=10, decimal_places=7, read_only=True)
    help_request_longitude = serializers.DecimalField(source='help_request.longitude', max_digits=10, decimal_places=7, read_only=True)

    class Meta:
        model = VolunteerTask
        fields = [
            'id',
            'help_request',
            'help_request_description',
            'help_request_type',
            'help_request_address',
            'help_request_latitude',
            'help_request_longitude',
            'volunteer',
            'volunteer_name',
            'status',
            'status_display',
            'feedback',
            'assigned_at',
            'accepted_at',
            'completed_at',
        ]
        read_only_fields = ['assigned_at', 'accepted_at', 'completed_at']