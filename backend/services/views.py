from datetime import date

from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.utils import create_notification
from tasks.models import TaskCancellation
from tasks.cancellation import evaluate_cancellation
from .models import ServiceType, ServiceSubscription, ServiceVisit
from .serializers import (
    ServiceTypeSerializer, ServiceSubscriptionSerializer, ServiceVisitSerializer,
)
from . import scheduler


def _profile(user):
    return getattr(user, 'profile', None)


def is_admin(user):
    if user.is_superuser:
        return True
    profile = _profile(user)
    return bool(profile and profile.role == 'admin')


def _admins():
    return User.objects.filter(Q(profile__role='admin') | Q(is_superuser=True)).distinct()


class ServiceTypeViewSet(viewsets.ModelViewSet):
    """服务目录：所有登录用户可读，仅管理员可增删改。"""
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'category', 'default_frequency']
    search_fields = ['name', 'code', 'category']

    def _require_admin(self):
        if not is_admin(self.request.user):
            self.permission_denied(self.request, message='只有管理员可以维护服务目录')

    def perform_create(self, serializer):
        self._require_admin()
        serializer.save()

    def perform_update(self, serializer):
        self._require_admin()
        serializer.save()

    def perform_destroy(self, instance):
        self._require_admin()
        instance.delete()


class ServiceSubscriptionViewSet(viewsets.ModelViewSet):
    """服务计划：管理员全量管理；居民可为自己建立/查看。"""
    queryset = ServiceSubscription.objects.select_related('resident', 'service_type', 'created_by')
    serializer_class = ServiceSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'service_type', 'resident', 'frequency']
    search_fields = ['resident__username', 'service_type__name', 'address']

    def get_queryset(self):
        user = self.request.user
        base = ServiceSubscription.objects.select_related('resident', 'service_type', 'created_by')
        if is_admin(user):
            return base.all()
        profile = _profile(user)
        if profile and profile.role == 'resident':
            return base.filter(resident=user)
        return ServiceSubscription.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        profile = _profile(user)
        admin = is_admin(user)
        # 仅管理员或居民本人可创建服务计划（志愿者/其他角色一律拒绝，避免越权代订）
        if not admin and not (profile and profile.role == 'resident'):
            raise PermissionDenied('只有管理员或居民本人可以创建服务计划')
        extra = {'created_by': user}
        if not admin:
            # 非管理员（居民）只能给自己订阅，忽略请求体里的 resident
            extra['resident'] = user
        elif not serializer.validated_data.get('resident'):
            raise ValidationError('管理员创建服务计划时必须指定受益居民')
        if not serializer.validated_data.get('start_date'):
            extra['start_date'] = date.today()
        sub = serializer.save(**extra)
        # 地址缺省取居民资料地址
        if not sub.address:
            rp = _profile(sub.resident)
            if rp and getattr(rp, 'address', ''):
                sub.address = rp.address
                sub.save(update_fields=['address'])

    def perform_update(self, serializer):
        # 非管理员不能改受益居民（防止把自己的计划改派到他人名下）
        if is_admin(self.request.user):
            serializer.save()
        else:
            serializer.save(resident=serializer.instance.resident)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        """暂停/恢复服务计划。管理员可操作任意计划，居民仅可操作自己的。

        权限天然由 get_queryset 收敛：居民 get_object 只能取到本人计划，
        取不到他人计划（404）；志愿者/其他角色一律取不到。
        """
        sub = self.get_object()
        sub.is_active = not sub.is_active
        sub.save(update_fields=['is_active'])
        return Response({
            'message': '已恢复该服务计划' if sub.is_active else '已暂停该服务计划',
            'is_active': sub.is_active,
            'subscription': ServiceSubscriptionSerializer(sub).data,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='generate-visits')
    def generate_visits(self, request):
        """管理员触发：为所有到期服务计划生成工单并自动轮流派单。"""
        if not is_admin(request.user):
            return Response({'message': '只有管理员可以生成排班'}, status=status.HTTP_403_FORBIDDEN)
        created = scheduler.generate_due_visits()
        assigned = sum(1 for v in created if v.volunteer_id)
        return Response({
            'message': f'本次生成 {len(created)} 张工单，其中 {assigned} 张已自动派单。',
            'created': len(created),
            'assigned': assigned,
            'unassigned': len(created) - assigned,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='generate-now')
    def generate_now(self, request, pk=None):
        """管理员对单个计划立即生成一张工单（忽略周期到期判断）。"""
        if not is_admin(request.user):
            return Response({'message': '只有管理员可以生成工单'}, status=status.HTTP_403_FORBIDDEN)
        sub = self.get_object()
        if scheduler.has_open_visit(sub):
            return Response({'message': '该计划已有进行中的工单'}, status=status.HTTP_400_BAD_REQUEST)
        visit = scheduler.create_visit_for(sub, date.today())
        return Response({
            'message': '已生成工单' + ('并自动派单' if visit.volunteer_id else '，暂无匹配志愿者'),
            'visit': ServiceVisitSerializer(visit).data,
        }, status=status.HTTP_200_OK)


class ServiceVisitViewSet(viewsets.ModelViewSet):
    """上门服务工单：管理员全量；志愿者见自己的；居民见自己的。"""
    queryset = ServiceVisit.objects.select_related('resident', 'volunteer', 'service_type', 'subscription')
    serializer_class = ServiceVisitSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'service_type', 'volunteer', 'resident', 'scheduled_date']
    search_fields = ['resident__username', 'volunteer__username', 'service_type__name', 'address']
    ordering_fields = ['scheduled_date', 'created_at', 'completed_at']

    def get_queryset(self):
        user = self.request.user
        base = ServiceVisit.objects.select_related('resident', 'volunteer', 'service_type', 'subscription')
        if is_admin(user):
            qs = base.all()
        else:
            profile = _profile(user)
            if profile is None:
                return ServiceVisit.objects.none()
            if profile.role == 'volunteer':
                qs = base.filter(volunteer=user)
            elif profile.role == 'resident':
                qs = base.filter(resident=user)
            else:
                return ServiceVisit.objects.none()

        # ?upcoming=1 只看今天及以后、尚未完成（已排班/服务中）的工单
        if self.request.query_params.get('upcoming') in ('1', 'true'):
            today = timezone.now().date()
            qs = qs.filter(scheduled_date__gte=today, status__in=['assigned', 'processing'])
        return qs

    # 工单只能由系统排班生成、经状态机 action 流转；关闭默认的直接增删改，
    # 防止志愿者用 DELETE 绕过取消管控、居民用 PATCH 伪造健康记录。
    def create(self, request, *args, **kwargs):
        return Response({'message': '上门工单由系统排班生成，不支持直接创建'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response({'message': '只有管理员可以修改工单'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response({'message': '只有管理员可以修改工单'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            return Response({'message': '只有管理员可以删除工单'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """志愿者开始服务：已排班 -> 服务中。"""
        visit = self.get_object()
        profile = _profile(request.user)
        if profile is None or profile.role != 'volunteer' or visit.volunteer_id != request.user.id:
            return Response({'message': '只能开始分配给自己的服务'}, status=status.HTTP_403_FORBIDDEN)
        if visit.status != 'assigned':
            return Response({'message': '当前状态不可开始'}, status=status.HTTP_400_BAD_REQUEST)
        visit.status = 'processing'
        visit.started_at = timezone.now()
        visit.save(update_fields=['status', 'started_at'])
        return Response({'message': '已开始服务', 'visit': ServiceVisitSerializer(visit).data})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """志愿者完成服务并录入服务/健康记录（可含拍照凭证）。"""
        visit = self.get_object()
        profile = _profile(request.user)
        if profile is None or profile.role != 'volunteer' or visit.volunteer_id != request.user.id:
            return Response({'message': '只能完成分配给自己的服务'}, status=status.HTTP_403_FORBIDDEN)
        if visit.status not in ['assigned', 'processing']:
            return Response({'message': '当前状态不可完成'}, status=status.HTTP_400_BAD_REQUEST)

        visit.feedback = request.data.get('feedback', '') or ''
        visit.health_note = request.data.get('health_note', '') or ''
        for f in ['systolic', 'diastolic', 'heart_rate']:
            val = request.data.get(f)
            if val not in (None, ''):
                try:
                    setattr(visit, f, int(val))
                except (TypeError, ValueError):
                    pass
        temp = request.data.get('temperature')
        if temp not in (None, ''):
            try:
                visit.temperature = float(temp)
            except (TypeError, ValueError):
                pass
        if 'photo' in request.FILES:
            visit.completion_photo = request.FILES['photo']

        visit.status = 'completed'
        visit.completed_at = timezone.now()
        visit.save()

        create_notification(
            recipient=visit.resident,
            title='上门服务已完成',
            content=f'志愿者 {request.user.username} 已完成「{visit.service_type.name}」服务。',
            category='service', related_type='service_visit', related_id=visit.id,
        )
        return Response({'message': '服务已完成', 'visit': ServiceVisitSerializer(visit).data})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """志愿者申请取消上门服务（需选原因）。与应急任务共用月度取消管控：
        本月取消 >5 警告，>7 撤销志愿者资格。取消后系统自动轮换到下一位志愿者。"""
        profile = _profile(request.user)
        if profile is None or profile.role != 'volunteer':
            return Response({'message': '只有志愿者可以申请取消服务'}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', 'other')
        if reason not in [c[0] for c in TaskCancellation.REASON_CHOICES]:
            reason = 'other'
        note = request.data.get('note', '') or ''

        replacement = None
        with transaction.atomic():
            try:
                visit = ServiceVisit.objects.select_for_update().select_related(
                    'subscription', 'service_type', 'resident'
                ).get(pk=pk)
            except ServiceVisit.DoesNotExist:
                return Response({'message': '工单不存在'}, status=status.HTTP_404_NOT_FOUND)

            if visit.volunteer_id != request.user.id:
                return Response({'message': '不能取消其他志愿者的服务'}, status=status.HTTP_403_FORBIDDEN)
            if visit.status not in ['assigned', 'processing']:
                return Response({'message': '当前状态不可取消'}, status=status.HTTP_400_BAD_REQUEST)

            TaskCancellation.objects.create(
                volunteer=request.user, visit=visit, reason=reason, note=note
            )

            visit.status = 'cancelled'
            visit.save(update_fields=['status'])

            # 自动轮换到下一位志愿者，生成替补工单
            community = scheduler.community_of(visit.resident)
            next_vol = scheduler.pick_volunteer(
                visit.service_type, community, exclude_ids=[request.user.id]
            )
            replacement = ServiceVisit.objects.create(
                subscription=visit.subscription, service_type=visit.service_type,
                resident=visit.resident, volunteer=next_vol,
                scheduled_date=visit.scheduled_date, status='assigned',
                address=visit.address, latitude=visit.latitude, longitude=visit.longitude,
            )

            # 月度取消管控（与应急任务共用），阈值与撤销逻辑见 tasks.cancellation
            month_count, warned, revoked = evaluate_cancellation(request.user)

        scheduler._notify_new_visit(replacement)

        reason_display = dict(TaskCancellation.REASON_CHOICES).get(reason, reason)
        note_part = ('｜' + note) if note else ''
        admins = _admins()
        for admin in admins:
            create_notification(
                recipient=admin, title='志愿者取消上门服务',
                content=f'志愿者 {request.user.username} 取消了 {visit.resident.username} 的'
                        f'「{visit.service_type.name}」服务，原因：{reason_display}{note_part}。'
                        f'本月第 {month_count} 次取消，系统已自动改派。',
                category='service', related_type='service_visit', related_id=visit.id,
            )

        if revoked:
            create_notification(
                recipient=request.user, title='志愿者资格已被撤销',
                content=f'你本月已取消任务 {month_count} 次，超过上限，账号资格被撤销，请联系管理员重新申请账号。',
                category='service', related_type='user', related_id=request.user.id,
            )
            message = f'取消成功。本月取消已达 {month_count} 次，账号资格已被撤销，请重新申请账号。'
        elif warned:
            create_notification(
                recipient=request.user, title='取消次数超限警告',
                content=f'你本月已取消任务 {month_count} 次（上限 5 次）。再取消 2 次将被撤销志愿者资格。',
                category='service', related_type='user', related_id=request.user.id,
            )
            message = f'取消成功。注意：本月已取消 {month_count} 次，再取消 2 次将被撤销资格。'
        else:
            message = f'取消成功。本月已取消 {month_count} 次（上限 5 次）。'

        return Response({
            'message': message,
            'monthly_cancel_count': month_count,
            'warned': warned,
            'revoked': revoked,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reassign(self, request, pk=None):
        """管理员改派工单给指定志愿者。"""
        if not is_admin(request.user):
            return Response({'message': '只有管理员可以改派'}, status=status.HTTP_403_FORBIDDEN)
        visit = self.get_object()
        if visit.status not in ['assigned', 'processing']:
            return Response({'message': '当前状态不可改派'}, status=status.HTTP_400_BAD_REQUEST)
        volunteer_id = request.data.get('volunteer_id')
        try:
            volunteer = User.objects.get(pk=volunteer_id, profile__role='volunteer', is_active=True)
        except User.DoesNotExist:
            return Response({'message': '指定志愿者不存在或不可用'}, status=status.HTTP_400_BAD_REQUEST)
        visit.volunteer = volunteer
        visit.status = 'assigned'
        visit.save(update_fields=['volunteer', 'status'])
        create_notification(
            recipient=volunteer, title='新的上门服务任务',
            content=f'管理员为你指派了 {visit.resident.username} 的「{visit.service_type.name}」服务。',
            category='service', related_type='service_visit', related_id=visit.id,
        )
        return Response({'message': '改派成功', 'visit': ServiceVisitSerializer(visit).data})
