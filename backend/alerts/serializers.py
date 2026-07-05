from rest_framework import serializers
from .models import Warning


class WarningSerializer(serializers.ModelSerializer):
    warning_type_display = serializers.CharField(source='get_warning_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    publisher_name = serializers.CharField(source='publisher.username', read_only=True)
    launch_emergency_plan = serializers.BooleanField(write_only=True, required=False, default=False)

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
            'launch_emergency_plan',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['publisher', 'publisher_name', 'created_at', 'updated_at']

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 4:
            raise serializers.ValidationError('预警标题不能少于 4 个字')
        if len(value) > 100:
            raise serializers.ValidationError('预警标题不能超过 100 个字')
        return value

    def validate_content(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('预警内容不能少于 10 个字，请写明灾害情况和防护建议')
        return value

    def create(self, validated_data):
        validated_data.pop('launch_emergency_plan', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('launch_emergency_plan', None)
        return super().update(instance, validated_data)
