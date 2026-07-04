from django.contrib.auth.models import User
from rest_framework import viewsets
from .models import Warning
from .serializers import WarningSerializer
from notifications.utils import create_notification


class WarningViewSet(viewsets.ModelViewSet):
    queryset = Warning.objects.all()
    serializer_class = WarningSerializer
    filterset_fields = ['warning_type', 'level', 'is_active', 'community']
    search_fields = ['title', 'content', 'community']
    ordering_fields = ['created_at', 'updated_at']

    def perform_create(self, serializer):
        warning = serializer.save(
            publisher=self.request.user if self.request.user.is_authenticated else None
        )

        # 通知居民和志愿者：有新的灾害预警
        users = User.objects.filter(
            profile__role__in=['resident', 'volunteer']
        )

        for user in users:
            create_notification(
                recipient=user,
                title='新的灾害预警',
                content=f'{warning.title}：{warning.content}',
                category='warning',
                related_type='warning',
                related_id=warning.id
            )