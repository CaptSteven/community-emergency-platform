import math
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

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
            # 志愿者只看：1）可认领的待处理求助；2）已经分配/认领给自己的求助。
            # 避免志愿者端看到其他志愿者正在处理的求助。
            return base_queryset.filter(
                Q(status='pending') | Q(volunteer_task__volunteer=user)
            ).distinct()

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
    def claim(self, request, pk=None):
        """志愿者自主认领待处理求助。

        鸿蒙志愿者端会直接调用 /api/help-requests/{id}/claim/。
        认领成功后立即生成/复用任务，并进入 processing，避免“端侧有按钮但后端 404”的问题。
        """
        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != 'volunteer':
            return Response({'message': '只有志愿者可以认领求助'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            try:
                help_request = HelpRequest.objects.select_for_update().select_related('resident').get(pk=pk)
            except HelpRequest.DoesNotExist:
                return Response({'message': '求助不存在'}, status=status.HTTP_404_NOT_FOUND)

            volunteer_profile = UserProfile.objects.select_for_update().get(user=request.user)

            if help_request.status != 'pending':
                return Response({'message': '只有待处理求助可以被志愿者认领'}, status=status.HTTP_400_BAD_REQUEST)

            if not volunteer_profile.is_available:
                return Response({'message': '你当前已有任务处理中，暂不能认领新的求助'}, status=status.HTTP_400_BAD_REQUEST)

            existing_task = VolunteerTask.objects.select_for_update().filter(help_request=help_request).first()
            now = timezone.now()

            if existing_task is not None:
                if existing_task.volunteer_id == request.user.id and existing_task.status in ['assigned', 'processing']:
                    task = existing_task
                    task.status = 'processing'
                    task.accepted_at = task.accepted_at or now
                    task.save(update_fields=['status', 'accepted_at'])
                elif existing_task.volunteer_id is None and existing_task.status in ['assigned', 'cancelled']:
                    task = existing_task
                    task.volunteer = request.user
                    task.status = 'processing'
                    task.feedback = ''
                    task.accepted_at = now
                    task.completed_at = None
                    task.save(update_fields=['volunteer', 'status', 'feedback', 'accepted_at', 'completed_at'])
                else:
                    assigned_name = existing_task.volunteer.username if existing_task.volunteer else '其他志愿者'
                    return Response({
                        'message': f'该求助已存在任务，不能重复认领。当前任务状态：{existing_task.get_status_display()}，志愿者：{assigned_name}',
                        'task_id': existing_task.id,
                        'task_status': existing_task.status,
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                task = VolunteerTask.objects.create(
                    help_request=help_request,
                    volunteer=request.user,
                    status='processing',
                    accepted_at=now,
                )

            help_request.status = 'processing'
            help_request.save(update_fields=['status', 'updated_at'])

            volunteer_profile.is_available = False
            volunteer_profile.save(update_fields=['is_available'])

        create_notification(
            recipient=help_request.resident,
            title='志愿者已认领求助',
            content=f'你的求助已由志愿者 {request.user.username} 认领，正在处理中。',
            category='help_request',
            related_type='help_request',
            related_id=help_request.id
        )

        return Response({
            'message': '认领成功',
            'help_request': HelpRequestSerializer(help_request).data,
            'task': {
                'id': task.id,
                'volunteer_id': request.user.id,
                'volunteer_name': request.user.username,
                'status': task.status,
            }
        }, status=status.HTTP_200_OK)

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

            existing_task = VolunteerTask.objects.select_for_update().filter(
                help_request=help_request
            ).first()

            # 说明：系统允许存在“未绑定志愿者的待抢单任务”。
            # 这种任务虽然已有 VolunteerTask 记录，但 volunteer 为空，不能算已经完成管理员派单。
            # 旧逻辑只要 exists() 就拒绝，导致地图拖拽派单误报“该求助已经分配过任务”。
            reusable_open_task = (
                existing_task is not None
                and existing_task.volunteer_id is None
                and existing_task.status in ['assigned', 'cancelled']
            )

            if help_request.status not in ['pending', 'assigned']:
                return Response({'message': '只有待处理或待分配的求助才能分配志愿者'}, status=status.HTTP_400_BAD_REQUEST)

            if existing_task is not None and not reusable_open_task:
                assigned_name = existing_task.volunteer.username if existing_task.volunteer else '未知志愿者'
                return Response({
                    'message': f'该求助已经存在有效任务，不能重复分配。当前任务状态：{existing_task.get_status_display()}，志愿者：{assigned_name}',
                    'task_id': existing_task.id,
                    'task_status': existing_task.status,
                    'volunteer_id': existing_task.volunteer_id,
                }, status=status.HTTP_400_BAD_REQUEST)

            if not volunteer_profile.is_available:
                return Response({'message': '该志愿者当前不可用'}, status=status.HTTP_400_BAD_REQUEST)

            if reusable_open_task:
                task = existing_task
                task.volunteer = volunteer
                task.status = 'assigned'
                task.feedback = ''
                task.accepted_at = None
                task.completed_at = None
                task.save(update_fields=['volunteer', 'status', 'feedback', 'accepted_at', 'completed_at'])
            else:
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

    @action(detail=True, methods=['post'], url_path='map-dispatch')
    def map_dispatch(self, request, pk=None):
        """一图指挥舱地图拖拽派单接口。

        前端将空闲志愿者 Marker 拖动到待处理求助点附近后调用该接口。
        后端复用 assign 的事务锁、状态校验和通知逻辑，避免绕过并发安全检查。
        """
        response = self.assign(request, pk)
        if response.status_code == status.HTTP_200_OK:
            response.data['message'] = '地图拖拽派单成功'
            response.data['dispatch_mode'] = 'map_drag'
        return response

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
