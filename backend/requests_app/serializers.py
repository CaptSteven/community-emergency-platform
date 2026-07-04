from rest_framework import serializers
from .models import HelpRequest


class HelpRequestSerializer(serializers.ModelSerializer):
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    resident_name = serializers.CharField(source='resident.username', read_only=True)

    class Meta:
        model = HelpRequest
        fields = [
            'id',
            'resident',
            'resident_name',
            'request_type',
            'request_type_display',
            'urgency',
            'urgency_display',
            'description',
            'address',
            'latitude',
            'longitude',
            'status',
            'status_display',
            'created_at',
            'updated_at',
            'completed_at',
        ]

        # 这些字段不允许前端直接修改
        read_only_fields = [
            'resident',
            'status',
            'created_at',
            'updated_at',
            'completed_at',
        ]