from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notifications.utils import create_notification
from .models import VolunteerTask
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

        if user.is_superuser:
            return VolunteerTask.objects.all()

        profile = getattr(user, 'profile', None)

        if profile is None:
            return VolunteerTask.objects.none()

        if profile.role == 'admin':
            return VolunteerTask.objects.all()

        if profile.role == 'volunteer':
            return VolunteerTask.objects.filter(volunteer=user)

        return VolunteerTask.objects.none()

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        task = self.get_object()

        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != 'volunteer':
            return Response({
                'message': '只有志愿者可以接单'
            }, status=status.HTTP_403_FORBIDDEN)

        if task.volunteer is None:
            task.volunteer = request.user

        if task.volunteer != request.user:
            return Response({
                'message': '该任务已分配给其他志愿者'
            }, status=status.HTTP_403_FORBIDDEN)

        task.status = 'processing'
        task.accepted_at = timezone.now()
        task.save()

        help_request = task.help_request
        help_request.status = 'processing'
        help_request.save()

        return Response({
            'message': '接单成功',
            'task': VolunteerTaskSerializer(task).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()

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