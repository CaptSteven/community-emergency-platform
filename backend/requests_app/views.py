from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notifications.utils import create_notification

from .models import HelpRequest
from .serializers import HelpRequestSerializer
from tasks.models import VolunteerTask


class HelpRequestViewSet(viewsets.ModelViewSet):
    queryset = HelpRequest.objects.all()
    serializer_class = HelpRequestSerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = ['request_type', 'urgency', 'status', 'resident']
    search_fields = ['description', 'address', 'resident__username']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        user = self.request.user

        # 超级管理员可以查看所有求助
        if user.is_superuser:
            return HelpRequest.objects.all()

        profile = getattr(user, 'profile', None)

        if profile is None:
            return HelpRequest.objects.none()

        # 管理员可以查看所有求助
        if profile.role == 'admin':
            return HelpRequest.objects.all()

        # 居民只能查看自己的求助
        if profile.role == 'resident':
            return HelpRequest.objects.filter(resident=user)

        # 志愿者可以查看未完成的求助，便于了解待处理情况
        if profile.role == 'volunteer':
            return HelpRequest.objects.exclude(status='completed')

        return HelpRequest.objects.none()

    def perform_create(self, serializer):
        help_request = serializer.save(
            resident=self.request.user,
            status='pending'
        )

        # 通知所有管理员：有新的居民求助
        admins = User.objects.filter(profile__role='admin')

        for admin in admins:
            create_notification(
                recipient=admin,
                title='新的居民求助',
                content=f'{self.request.user.username} 提交了新的求助：{help_request.description}',
                category='help_request',
                related_type='help_request',
                related_id=help_request.id
            )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        管理员分配求助任务给志愿者
        请求示例：
        {
            "volunteer_id": 3
        }
        """
        user = request.user
        profile = getattr(user, 'profile', None)

        # 只有管理员或超级管理员可以分配任务
        if not user.is_superuser:
            if profile is None or profile.role != 'admin':
                return Response({
                    'message': '只有管理员可以分配任务'
                }, status=status.HTTP_403_FORBIDDEN)

        help_request = self.get_object()

        volunteer_id = request.data.get('volunteer_id')

        if not volunteer_id:
            return Response({
                'message': '缺少 volunteer_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            volunteer = User.objects.get(id=volunteer_id)
        except User.DoesNotExist:
            return Response({
                'message': '志愿者用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        volunteer_profile = getattr(volunteer, 'profile', None)

        if volunteer_profile is None or volunteer_profile.role != 'volunteer':
            return Response({
                'message': '该用户不是志愿者'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not volunteer_profile.is_available:
            return Response({
                'message': '该志愿者当前不可用'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 如果这个求助已经有任务，则更新任务；否则创建任务
        task, created = VolunteerTask.objects.get_or_create(
            help_request=help_request,
            defaults={
                'volunteer': volunteer,
                'status': 'assigned'
            }
        )

        if not created:
            task.volunteer = volunteer
            task.status = 'assigned'
            task.feedback = ''
            task.accepted_at = None
            task.completed_at = None
            task.save()

        # 更新求助状态
        help_request.status = 'assigned'
        help_request.save()

        # 通知志愿者：有新的任务
        create_notification(
            recipient=volunteer,
            title='新的救助任务',
            content=f'你收到一条新的救助任务：{help_request.description}',
            category='task',
            related_type='task',
            related_id=task.id
        )

        # 通知居民：求助已分配志愿者
        create_notification(
            recipient=help_request.resident,
            title='求助已分配',
            content=f'你的求助已分配给志愿者 {volunteer.username}，请等待处理。',
            category='help_request',
            related_type='help_request',
            related_id=help_request.id
        )

        return Response({
            'message': '任务分配成功',
            'help_request': HelpRequestSerializer(help_request).data,
            'task': {
                'id': task.id,
                'volunteer_id': volunteer.id,
                'volunteer_name': volunteer.username,
                'status': task.status,
            }
        }, status=status.HTTP_200_OK)