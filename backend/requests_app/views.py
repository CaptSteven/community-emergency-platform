import math
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


REQUEST_KEYWORDS = {
    'medical': ['医疗', '急救', '心脏', '发烧', '老人', '药', '救护'],
    'material': ['物资', '食物', '饮水', '干粮', '药品', '棉被'],
    'transfer': ['转移', '疏散', '撤离', '车辆'],
    'trapped': ['被困', '困住', '楼道', '电梯', '塌方'],
    'fire': ['火灾', '着火', '烟雾', '灭火'],
    'flood': ['积水', '内涝', '洪水', '排水'],
    'elderly': ['老人', '独居', '行动不便'],
    'child': ['儿童', '孩子', '走失'],
}


def build_ai_summary(help_request):
    """轻量级本地智能摘要。后续可替换为文心一言/千问等 LLM API。"""
    text = f'{help_request.get_request_type_display()} {help_request.description or ""} {help_request.address or ""}'
    hits = []
    for words in REQUEST_KEYWORDS.values():
        for word in words:
            if word in text and word not in hits:
                hits.append(word)
    urgency = help_request.get_urgency_display()
    request_type = help_request.get_request_type_display()
    key_part = '、'.join(hits[:4]) if hits else (help_request.description or '')[:18]
    return f'{urgency}｜{request_type}｜{key_part}'[:255]


def haversine_km(lng1, lat1, lng2, lat2):
    if None in [lng1, lat1, lng2, lat2]:
        return None
    lng1, lat1, lng2, lat2 = map(math.radians, [float(lng1), float(lat1), float(lng2), float(lat2)])
    dlng = lng2 - lng1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return round(6371.0088 * c, 2)


class HelpRequestViewSet(viewsets.ModelViewSet):
    queryset = HelpRequest.objects.all()
    serializer_class = HelpRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    filterset_fields = ['request_type', 'urgency', 'status', 'resident']
    search_fields = [
        'description',
        'ai_summary',
        'address',
        'resident__username',
        'resident__profile__phone'
    ]
    ordering_fields = ['created_at', 'updated_at', 'urgency']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        base_queryset = HelpRequest.objects.select_related('resident', 'resident__profile')

        if user.is_superuser:
            return base_queryset.all()

        profile = getattr(user, 'profile', None)

        if profile is None:
            return HelpRequest.objects.none()

        if profile.role == 'admin':
            return base_queryset.all()

        if profile.role == 'resident':
            return base_queryset.filter(resident=user)

        if profile.role == 'volunteer':
            return base_queryset.exclude(status='completed')

        return HelpRequest.objects.none()

    def perform_create(self, serializer):
        profile = getattr(self.request.user, 'profile', None)

        if profile is None or profile.role != 'resident':
            raise PermissionDenied('只有居民可以提交求助')

        help_request = serializer.save(
            resident=self.request.user,
            status='pending'
        )
        help_request.ai_summary = build_ai_summary(help_request)
        help_request.save(update_fields=['ai_summary'])

        admins = User.objects.filter(profile__role='admin')

        for admin in admins:
            create_notification(
                recipient=admin,
                title='新的居民求助',
                content=f'{self.request.user.username} 提交了新的求助：{help_request.ai_summary or help_request.description}',
                category='help_request',
                related_type='help_request',
                related_id=help_request.id
            )

    @action(detail=True, methods=['get'], url_path='recommend-volunteers')
    def recommend_volunteers(self, request, pk=None):
        """根据距离、空闲状态、社区匹配和擅长任务推荐前 3 名志愿者。"""
        help_request = self.get_object()
        volunteers = User.objects.filter(profile__role='volunteer').select_related('profile')
        request_keywords = REQUEST_KEYWORDS.get(help_request.request_type, [])
        result = []

        for volunteer in volunteers:
            profile = volunteer.profile
            distance = haversine_km(
                help_request.longitude,
                help_request.latitude,
                profile.current_longitude,
                profile.current_latitude,
            )

            score = 0
            reasons = []

            if profile.is_available:
                score += 45
                reasons.append('当前空闲')
            else:
                score -= 30
                reasons.append('当前忙碌')

            if distance is not None:
                distance_score = max(0, 35 - distance * 4)
                score += distance_score
                reasons.append(f'距离约 {distance} km')
            else:
                reasons.append('缺少实时位置')

            resident_profile = getattr(help_request.resident, 'profile', None)
            if profile.community and resident_profile and resident_profile.community == profile.community:
                score += 10
                reasons.append('同社区')

            skills = profile.skills or ''
            if any(word in skills for word in request_keywords):
                score += 10
                reasons.append('擅长相关任务')

            result.append({
                'id': volunteer.id,
                'username': volunteer.username,
                'phone': profile.phone,
                'community': profile.community,
                'skills': profile.skills,
                'is_available': profile.is_available,
                'current_latitude': profile.current_latitude,
                'current_longitude': profile.current_longitude,
                'distance_km': distance,
                'score': round(score, 2),
                'reasons': reasons,
            })

        result.sort(key=lambda item: item['score'], reverse=True)
        return Response(result[:3])

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        user = request.user
        profile = getattr(user, 'profile', None)

        is_admin = (
                user.is_superuser
                or user.is_staff
                or (profile is not None and profile.role == 'admin')
        )

        if not is_admin:
            return Response({'message': '只有管理员可以分配任务'}, status=status.HTTP_403_FORBIDDEN)

        volunteer_id = request.data.get('volunteer_id')

        if not volunteer_id:
            return Response({'message': '缺少 volunteer_id'}, status=status.HTTP_400_BAD_REQUEST)

        help_request = self.get_object()

        try:
            volunteer = User.objects.select_related('profile').get(id=volunteer_id, profile__role='volunteer')
        except User.DoesNotExist:
            return Response({'message': '志愿者用户不存在或该用户不是志愿者'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            help_request = HelpRequest.objects.select_for_update().get(id=help_request.id)
            volunteer_profile = UserProfile.objects.select_for_update().get(user=volunteer)

            if help_request.status != 'pending':
                return Response({'message': '只有待处理的求助才能分配志愿者'}, status=status.HTTP_400_BAD_REQUEST)

            if VolunteerTask.objects.filter(help_request=help_request).exists():
                return Response({'message': '该求助已经分配过任务，不能重复分配'}, status=status.HTTP_400_BAD_REQUEST)

            if not volunteer_profile.is_available:
                return Response({'message': '该志愿者当前不可用'}, status=status.HTTP_400_BAD_REQUEST)

            task = VolunteerTask.objects.create(
                help_request=help_request,
                volunteer=volunteer,
                status='assigned'
            )

            help_request.status = 'assigned'
            help_request.save(update_fields=['status', 'updated_at'])

            volunteer_profile.is_available = False
            volunteer_profile.save(update_fields=['is_available'])

            create_notification(
                recipient=volunteer,
                title='新的救助任务',
                content=f'你收到一条新的救助任务：{help_request.ai_summary or help_request.description}',
                category='task',
                related_type='task',
                related_id=task.id
            )

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
            return Response({'message': '你不能取消其他人的求助'}, status=status.HTTP_403_FORBIDDEN)

        if help_request.status in ['completed', 'cancelled']:
            return Response({'message': '已完成或已取消的求助不能重复取消'}, status=status.HTTP_400_BAD_REQUEST)

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
