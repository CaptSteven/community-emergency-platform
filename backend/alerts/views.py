from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import viewsets
from .models import Warning
from .serializers import WarningSerializer
from notifications.utils import create_notification
from resources.models import Shelter
from emergency_backend.permissions import IsAdminOrReadOnly


class WarningViewSet(viewsets.ModelViewSet):
    queryset = Warning.objects.all()
    serializer_class = WarningSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['warning_type', 'level', 'is_active', 'community']
    search_fields = ['title', 'content', 'community']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        launch_plan = bool(serializer.validated_data.get('launch_emergency_plan'))
        with transaction.atomic():
            warning = serializer.save(
                publisher=self.request.user if self.request.user.is_authenticated else None
            )

            users = User.objects.filter(profile__role__in=['resident', 'volunteer'])
            for user in users:
                role = getattr(getattr(user, 'profile', None), 'role', '')

                if warning.level == 'red':
                    if role == 'volunteer':
                        title = '红色预警待命提醒'
                        content = (
                            f'【红色预警】{warning.title}\n\n'
                            f'{warning.content}\n\n'
                            '请保持手机在线，关注后续任务调度，提前做好服务准备。'
                        )
                    else:
                        title = '红色预警强提醒'
                        content = (
                            f'【红色预警】{warning.title}\n\n'
                            f'{warning.content}\n\n'
                            '请立即关注社区通知，注意自身安全，必要时前往开放避难点。'
                        )
                else:
                    title = '新的灾害预警'
                    content = f'{warning.title}：{warning.content}'

                create_notification(
                    recipient=user,
                    title=title,
                    content=content,
                    category='warning',
                    related_type='warning',
                    related_id=warning.id
                )

            if warning.level == 'red' and launch_plan:
                self._launch_emergency_plan(warning)

    def _launch_emergency_plan(self, warning):
        """红色预警联动预案：开放避难点、强提醒居民、志愿者待命。"""
        Shelter.objects.filter(is_available=False).update(is_available=True)

        residents = User.objects.filter(profile__role='resident')
        volunteers = User.objects.filter(profile__role='volunteer')
        admins = User.objects.filter(profile__role='admin')

        for resident in residents:
            create_notification(
                recipient=resident,
                title='应急预案已启动',
                content=f'{warning.title} 已启动应急预案，请关注社区通知，必要时前往开放避难点。',
                category='system',
                related_type='warning',
                related_id=warning.id
            )

        for volunteer in volunteers:
            create_notification(
                recipient=volunteer,
                title='红色预警待命指令',
                content=f'{warning.title} 已启动应急预案，请保持在线，等待社区管理员调度。',
                category='task',
                related_type='warning',
                related_id=warning.id
            )

        for admin in admins:
            create_notification(
                recipient=admin,
                title='应急预案已联动启动',
                content='系统已自动开放可用避难点，并向居民和志愿者发送联动通知。',
                category='system',
                related_type='warning',
                related_id=warning.id
            )
