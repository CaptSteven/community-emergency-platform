from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)

        queryset = Notification.objects.all()

        # 超级管理员可以看所有消息
        if user.is_superuser:
            pass
        # 普通管理员可以看所有消息
        elif profile and profile.role == 'admin':
            pass
        # 居民和志愿者只能看自己的消息
        else:
            queryset = queryset.filter(recipient=user)

        category = self.request.query_params.get('category')
        is_read = self.request.query_params.get('is_read')

        if category:
            queryset = queryset.filter(category=category)

        if is_read == 'true':
            queryset = queryset.filter(is_read=True)

        if is_read == 'false':
            queryset = queryset.filter(is_read=False)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()

        return Response({
            'message': '已标记为已读'
        })

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        queryset = self.get_queryset()
        count = queryset.filter(is_read=False).update(is_read=True)

        return Response({
            'message': '全部标记为已读',
            'count': count
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()

        return Response({
            'unread_count': count
        })