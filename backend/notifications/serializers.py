from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )

    recipient_name = serializers.CharField(
        source='recipient.username',
        read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'recipient_name',
            'title',
            'content',
            'category',
            'category_display',
            'is_read',
            'related_type',
            'related_id',
            'created_at',
        ]

        read_only_fields = [
            'recipient',
            'recipient_name',
            'category_display',
            'created_at',
        ]