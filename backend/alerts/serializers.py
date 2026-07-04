from rest_framework import serializers
from .models import Warning


class WarningSerializer(serializers.ModelSerializer):
    warning_type_display = serializers.CharField(source='get_warning_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    publisher_name = serializers.CharField(source='publisher.username', read_only=True)

    class Meta:
        model = Warning
        fields = [
            'id',
            'title',
            'warning_type',
            'warning_type_display',
            'level',
            'level_display',
            'content',
            'community',
            'publisher',
            'publisher_name',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']