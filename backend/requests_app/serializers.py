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
            'ai_summary',
            'address',
            'latitude',
            'longitude',
            'status',
            'status_display',
            'created_at',
            'updated_at',
            'completed_at',
            'completion_photo',
        ]

        read_only_fields = [
            'resident',
            'status',
            'ai_summary',
            'created_at',
            'updated_at',
            'completed_at',
            'completion_photo',
        ]

    def validate(self, attrs):
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')

        if latitude is not None and not (-90 <= float(latitude) <= 90):
            raise serializers.ValidationError({'latitude': '纬度必须在 -90 到 90 之间'})

        if longitude is not None and not (-180 <= float(longitude) <= 180):
            raise serializers.ValidationError({'longitude': '经度必须在 -180 到 180 之间'})

        if (latitude is None) ^ (longitude is None):
            raise serializers.ValidationError('经度和纬度必须同时填写，避免地图定位错误')

        description = attrs.get('description')
        if description is not None and len(description.strip()) < 6:
            raise serializers.ValidationError({'description': '求助描述不能少于 6 个字，请写清具体情况'})

        return attrs
