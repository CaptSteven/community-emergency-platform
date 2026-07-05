from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import HelpRequest
from .serializers import HelpRequestSerializer
from tasks.models import VolunteerTask
from users.models import UserProfile
from notifications.utils import create_notification


class HelpRequestViewSet(viewsets.ModelViewSet):
    queryset = HelpRequest.objects.all()
    serializer_class = HelpRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    filterset_fields = ['request_type', 'urgency', 'status', 'resident']
    search_fields = [
        'description',
        'address',
        'resident__username',
        'resident__profile__phone'
    ]
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
        profile = getattr(self.request.user, 'profile', None)

        if profile is None or profile.role != 'resident':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只有居民可以提交求助')

        help_request = serializer.save(
            resident=self.request.user,
            status='pending'
        )

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

        # 只有管理员、Django staff 或超级管理员可以分配任务
        is_admin = (
                user.is_superuser
                or user.is_staff
                or (profile is not None and profile.role == 'admin')
        )

        if not is_admin:
            return Response({
                'message': '只有管理员可以分配任务'
            }, status=status.HTTP_403_FORBIDDEN)

        volunteer_id = request.data.get('volunteer_id')

        if not volunteer_id:
            return Response({
                'message': '缺少 volunteer_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 先确认求助对象存在，同时复用 ViewSet 原本的 get_object 逻辑
        help_request = self.get_object()

        try:
            volunteer = User.objects.select_related('profile').get(
                id=volunteer_id,
                profile__role='volunteer'
            )
        except User.DoesNotExist:
            return Response({
                'message': '志愿者用户不存在或该用户不是志愿者'
            }, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            # 对当前求助记录加锁，防止两个管理员同时分配同一条求助
            help_request = HelpRequest.objects.select_for_update().get(id=help_request.id)

            # 对志愿者资料加锁，防止同一个志愿者被同时分配多个任务
            volunteer_profile = UserProfile.objects.select_for_update().get(user=volunteer)

            if help_request.status != 'pending':
                return Response({
                    'message': '只有待处理的求助才能分配志愿者'
                }, status=status.HTTP_400_BAD_REQUEST)

            if VolunteerTask.objects.filter(help_request=help_request).exists():
                return Response({
                    'message': '该求助已经分配过任务，不能重复分配'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not volunteer_profile.is_available:
                return Response({
                    'message': '该志愿者当前不可用'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 创建志愿者任务
            task = VolunteerTask.objects.create(
                help_request=help_request,
                volunteer=volunteer,
                status='assigned'
            )

            # 更新求助状态
            help_request.status = 'assigned'
            help_request.save(update_fields=['status'])

            # 分配成功后，志愿者进入忙碌状态
            volunteer_profile.is_available = False
            volunteer_profile.save(update_fields=['is_available'])

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

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        help_request = self.get_object()
        user = request.user
        profile = getattr(user, 'profile', None)

        is_admin = user.is_superuser or user.is_staff or (profile and profile.role == 'admin')
        is_owner = help_request.resident == user

        if not is_admin and not is_owner:
            return Response({
                'message': '你不能取消其他人的求助'
            }, status=status.HTTP_403_FORBIDDEN)

        if help_request.status in ['completed', 'cancelled']:
            return Response({
                'message': '已完成或已取消的求助不能重复取消'
            }, status=status.HTTP_400_BAD_REQUEST)

        help_request.status = 'cancelled'
        help_request.save()

        if hasattr(help_request, 'volunteer_task'):
            task = help_request.volunteer_task
            task.status = 'cancelled'
            task.save()

            if task.volunteer and hasattr(task.volunteer, 'profile'):
                task.volunteer.profile.is_available = True
                task.volunteer.profile.save()

        create_notification(
            recipient=help_request.resident,
            title='求助已取消',
            content=f'你的求助已取消：{help_request.description}',
            category='help_request',
            related_type='help_request',
            related_id=help_request.id
        )

        return Response({
            'message': '求助已取消',
            'help_request': HelpRequestSerializer(help_request).data
        })