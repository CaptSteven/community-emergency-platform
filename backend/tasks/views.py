from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notifications.utils import create_notification
from users.models import UserProfile
from .models import VolunteerTask, TaskCancellation
from .serializers import VolunteerTaskSerializer


class VolunteerTaskViewSet(viewsets.ModelViewSet):
    queryset = VolunteerTask.objects.all()
    serializer_class = VolunteerTaskSerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = ['status', 'volunteer']
    search_fields = ['help_request__description', 'help_request__address', 'volunteer__username']
    ordering_fields = ['assigned_at', 'accepted_at', 'completed_at']

    def get_queryset(self):
        user = self.request.user
        base_queryset = VolunteerTask.objects.select_related('help_request', 'volunteer')

        if user.is_superuser:
            return base_queryset.all()

        profile = getattr(user, 'profile', None)

        if profile is None:
            return VolunteerTask.objects.none()

        if profile.role == 'admin':
            return base_queryset.all()

        if profile.role == 'volunteer':
            # 志愿者可查看：1）已分配给自己的任务；2）未绑定志愿者、可被抢单的任务。
            return base_queryset.filter(
                Q(volunteer=user) | Q(volunteer__isnull=True, status='assigned')
            )

        return VolunteerTask.objects.none()

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != 'volunteer':
            return Response({
                'message': '只有志愿者可以接单'
            }, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            try:
                # select_for_update 会在事务内锁住当前任务行，避免多个志愿者同时抢单时读到同一个旧状态。
                task = VolunteerTask.objects.select_for_update().select_related(
                    'help_request',
                    'volunteer'
                ).get(pk=pk)
            except VolunteerTask.DoesNotExist:
                return Response({
                    'message': '任务不存在'
                }, status=status.HTTP_404_NOT_FOUND)

            if task.volunteer_id is not None and task.volunteer_id != request.user.id:
                return Response({
                    'message': '该任务已分配给其他志愿者'
                }, status=status.HTTP_403_FORBIDDEN)

            if task.status == 'processing' and task.volunteer_id == request.user.id:
                return Response({
                    'message': '你已接单，请勿重复操作',
                    'task': VolunteerTaskSerializer(task).data
                }, status=status.HTTP_200_OK)

            if task.status != 'assigned':
                return Response({
                    'message': '当前任务状态不允许接单'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 锁定志愿者资料。未定向分配的抢单任务，需要确保志愿者当前仍空闲。
            volunteer_profile = UserProfile.objects.select_for_update().get(user=request.user)
            if task.volunteer_id is None and not volunteer_profile.is_available:
                return Response({
                    'message': '你当前已有任务处理中，暂不能抢单'
                }, status=status.HTTP_400_BAD_REQUEST)

            task.volunteer = request.user
            task.status = 'processing'
            task.accepted_at = timezone.now()
            task.save(update_fields=['volunteer', 'status', 'accepted_at'])

            volunteer_profile.is_available = False
            volunteer_profile.save(update_fields=['is_available'])

            help_request = task.help_request
            help_request.status = 'processing'
            help_request.save(update_fields=['status', 'updated_at'])

        create_notification(
            recipient=help_request.resident,
            title='志愿者已接单',
            content=f'你的求助已由志愿者 {request.user.username} 接单，正在处理中。',
            category='help_request',
            related_type='help_request',
            related_id=help_request.id
        )

        return Response({
            'message': '接单成功',
            'task': VolunteerTaskSerializer(task).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """志愿者申请取消强制分配的任务（需选择原因）。月取消>5 警告，再 2 次(>7) 撤销资格。"""
        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != 'volunteer':
            return Response({'message': '只有志愿者可以申请取消任务'}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', 'other')
        if reason not in [c[0] for c in TaskCancellation.REASON_CHOICES]:
            reason = 'other'
        note = request.data.get('note', '') or ''

        with transaction.atomic():
            try:
                task = VolunteerTask.objects.select_for_update().select_related('help_request', 'volunteer').get(pk=pk)
            except VolunteerTask.DoesNotExist:
                return Response({'message': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

            if task.volunteer_id != request.user.id:
                return Response({'message': '不能取消其他志愿者的任务'}, status=status.HTTP_403_FORBIDDEN)

            if task.status not in ['assigned', 'processing']:
                return Response({'message': '当前任务状态不可取消'}, status=status.HTTP_400_BAD_REQUEST)

            help_request = task.help_request
            TaskCancellation.objects.create(
                volunteer=request.user, task=task, help_request=help_request, reason=reason, note=note
            )

            task.status = 'cancelled'
            task.feedback = ''
            task.accepted_at = None
            task.completed_at = None
            task.save(update_fields=['status', 'feedback', 'accepted_at', 'completed_at'])

            # 求助回到待分配，供管理员重新指派
            help_request.status = 'pending'
            help_request.save(update_fields=['status', 'updated_at'])

            volunteer_profile = UserProfile.objects.select_for_update().get(user=request.user)
            volunteer_profile.is_available = True
            volunteer_profile.save(update_fields=['is_available'])

            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_count = TaskCancellation.objects.filter(
                volunteer=request.user, created_at__gte=month_start
            ).count()

            revoked = month_count > 7
            warned = (not revoked) and month_count > 5
            if revoked:
                request.user.is_active = False
                request.user.save(update_fields=['is_active'])

        reason_display = dict(TaskCancellation.REASON_CHOICES).get(reason, reason)
        note_part = ('｜' + note) if note else ''
        admins = User.objects.filter(Q(profile__role='admin') | Q(is_superuser=True)).distinct()

        for admin in admins:
            create_notification(
                recipient=admin,
                title='志愿者取消任务',
                content=f'志愿者 {request.user.username} 取消了求助 #{help_request.id} 的任务，原因：{reason_display}{note_part}。本月第 {month_count} 次取消。',
                category='task',
                related_type='help_request',
                related_id=help_request.id
            )

        if revoked:
            for admin in admins:
                create_notification(
                    recipient=admin, title='志愿者资格已撤销',
                    content=f'志愿者 {request.user.username} 本月取消任务达 {month_count} 次，已自动撤销其志愿者账号资格，需重新申请。',
                    category='task', related_type='user', related_id=request.user.id
                )
            create_notification(
                recipient=request.user, title='志愿者资格已被撤销',
                content=f'你本月已取消任务 {month_count} 次，超过上限，账号资格被撤销，请联系管理员重新申请账号。',
                category='task', related_type='user', related_id=request.user.id
            )
            message = f'取消成功。你本月取消已达 {month_count} 次，账号资格已被撤销，请重新申请账号。'
        elif warned:
            create_notification(
                recipient=request.user, title='取消次数超限警告',
                content=f'你本月已取消任务 {month_count} 次（上限 5 次）。请谨慎操作，再取消 2 次将被撤销志愿者资格。',
                category='task', related_type='user', related_id=request.user.id
            )
            for admin in admins:
                create_notification(
                    recipient=admin, title='志愿者取消超限',
                    content=f'志愿者 {request.user.username} 本月取消已达 {month_count} 次，已触发警告。',
                    category='task', related_type='user', related_id=request.user.id
                )
            message = f'取消成功。注意：本月已取消 {month_count} 次，超过 5 次上限，再取消 2 次将被撤销资格。'
        else:
            message = f'取消成功。本月已取消 {month_count} 次（上限 5 次）。'

        return Response({
            'message': message,
            'monthly_cancel_count': month_count,
            'warned': warned,
            'revoked': revoked,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()

        if task.status == 'completed':
            return Response({
                'message': '该任务已完成，不能重复完成'
            }, status=status.HTTP_400_BAD_REQUEST)

        if task.status == 'cancelled':
            return Response({
                'message': '该任务已取消，不能完成'
            }, status=status.HTTP_400_BAD_REQUEST)

        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != 'volunteer':
            return Response({
                'message': '只有志愿者可以完成任务'
            }, status=status.HTTP_403_FORBIDDEN)

        if task.volunteer != request.user:
            return Response({
                'message': '你不能完成其他志愿者的任务'
            }, status=status.HTTP_403_FORBIDDEN)

        feedback = request.data.get('feedback', '')

        task.status = 'completed'
        task.feedback = feedback
        task.completed_at = timezone.now()
        task.save()

        profile.is_available = True
        profile.save()

        help_request = task.help_request
        help_request.status = 'completed'
        help_request.completed_at = timezone.now()
        help_request.save()

        create_notification(
            recipient=help_request.resident,
            title='求助已完成',
            content=f'你的求助已由志愿者 {request.user.username} 处理完成。处理反馈：{feedback}',
            category='help_request',
            related_type='help_request',
            related_id=help_request.id
        )

        return Response({
            'message': '任务已完成',
            'task': VolunteerTaskSerializer(task).data
        }, status=status.HTTP_200_OK)
