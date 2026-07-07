from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from alerts.models import Warning


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
        # 已读状态属于收件人本人：管理员在 Web 端浏览全量消息时，不得替他人清掉未读
        if notification.recipient_id != request.user.id:
            return Response({'message': '只能标记自己的消息'}, status=status.HTTP_403_FORBIDDEN)
        notification.is_read = True
        notification.save()

        return Response({
            'message': '已标记为已读'
        })

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        # 只标记发给自己的消息，避免管理员一键把全平台用户的未读清零
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)

        return Response({
            'message': '全部标记为已读',
            'count': count
        })


    @action(detail=False, methods=['get'], url_path='red-alerts')
    def red_alerts(self, request):
        """返回当前登录用户尚未确认的红色预警强提醒。

        鸿蒙居民端和志愿者端会定时轮询该接口。只返回：
        1. 属于当前用户的未读消息；
        2. 消息关联对象是 warning；
        3. 对应预警仍处于 red + is_active 状态。
        """
        active_red_warning_ids = Warning.objects.filter(
            level='red',
            is_active=True
        ).values_list('id', flat=True)

        queryset = self.get_queryset().filter(
            category='warning',
            related_type='warning',
            related_id__in=active_red_warning_ids,
            is_read=False
        ).order_by('created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        # 未读数只统计发给自己的消息（管理员的全量视角仅用于浏览，不用于角标）
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()

        return Response({
            'unread_count': count
        })