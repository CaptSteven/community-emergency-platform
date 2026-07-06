from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, F
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from emergency_backend.permissions import IsAdminRole
from datetime import date

from alerts.models import Warning
from requests_app.models import HelpRequest
from tasks.models import VolunteerTask
from resources.models import Shelter, Material
from users.models import UserProfile


def build_choice_stats(model, field_name, choices):
    """
    通用统计函数：
    例如统计 status、request_type、urgency、level 等 choices 字段
    """
    raw_data = model.objects.values(field_name).annotate(count=Count('id'))

    count_map = {
        item[field_name]: item['count']
        for item in raw_data
    }

    result = []
    for value, label in choices:
        result.append({
            'key': value,
            'label': label,
            'count': count_map.get(value, 0)
        })

    return result


class OverviewAPIView(APIView):
    """
    数据大屏总览
    """

    # 如果你已经做了管理员权限控制，就保留这一行
    permission_classes = [IsAdminRole]

    def get(self, request):
        today = date.today()

        help_request_count = HelpRequest.objects.count()
        completed_request_count = HelpRequest.objects.filter(status='completed').count()
        pending_request_count = HelpRequest.objects.filter(status='pending').count()
        assigned_request_count = HelpRequest.objects.filter(status='assigned').count()
        processing_request_count = HelpRequest.objects.filter(status='processing').count()
        cancelled_request_count = HelpRequest.objects.filter(status='cancelled').count()

        today_request_count = HelpRequest.objects.filter(
            created_at__date=today
        ).count()

        critical_pending_request_count = HelpRequest.objects.filter(
            status='pending',
            urgency__in=['high', 'critical']
        ).count()

        task_count = VolunteerTask.objects.count()
        completed_task_count = VolunteerTask.objects.filter(status='completed').count()
        processing_task_count = VolunteerTask.objects.filter(status='processing').count()
        assigned_task_count = VolunteerTask.objects.filter(status='assigned').count()

        if task_count == 0:
            task_completion_rate = 0
        else:
            task_completion_rate = round(completed_task_count / task_count * 100, 2)

        volunteer_count = UserProfile.objects.filter(role='volunteer').count()
        available_volunteer_count = UserProfile.objects.filter(
            role='volunteer',
            is_available=True
        ).count()

        material_count = Material.objects.count()
        low_stock_material_count = Material.objects.filter(
            quantity__lte=F('warning_quantity')
        ).count()

        today_date = timezone.now().date()
        expired_material_count = Material.objects.exclude(
            expire_date__isnull=True
        ).filter(expire_date__lt=today_date).count()
        expiring_material_count = sum(
            1 for item in Material.objects.exclude(expire_date__isnull=True).filter(expire_date__gte=today_date)
            if (item.expire_date - today_date).days <= item.expiry_warning_days
        )

        shelter_count = Shelter.objects.count()
        available_shelter_count = Shelter.objects.filter(is_available=True).count()

        data = {
            # 用户统计
            'user_count': User.objects.count(),
            'resident_count': UserProfile.objects.filter(role='resident').count(),
            'volunteer_count': volunteer_count,
            'available_volunteer_count': available_volunteer_count,
            'admin_count': UserProfile.objects.filter(role='admin').count(),

            # 预警统计
            'warning_count': Warning.objects.count(),
            'active_warning_count': Warning.objects.filter(is_active=True).count(),

            # 求助统计
            'help_request_count': help_request_count,
            'pending_request_count': pending_request_count,
            'assigned_request_count': assigned_request_count,
            'processing_request_count': processing_request_count,
            'completed_request_count': completed_request_count,
            'cancelled_request_count': cancelled_request_count,
            'today_request_count': today_request_count,
            'critical_pending_request_count': critical_pending_request_count,

            # 任务统计
            'task_count': task_count,
            'assigned_task_count': assigned_task_count,
            'processing_task_count': processing_task_count,
            'completed_task_count': completed_task_count,
            'task_completion_rate': task_completion_rate,

            # 资源统计
            'shelter_count': shelter_count,
            'available_shelter_count': available_shelter_count,
            'material_count': material_count,
            'low_stock_material_count': low_stock_material_count,
            'expired_material_count': expired_material_count,
            'expiring_material_count': expiring_material_count,
        }

        return Response(data)


class HelpRequestStatusStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    求助状态统计
    """
    def get(self, request):
        data = build_choice_stats(
            HelpRequest,
            'status',
            HelpRequest.STATUS_CHOICES
        )
        return Response(data)


class HelpRequestTypeStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    求助类型统计
    """
    def get(self, request):
        data = build_choice_stats(
            HelpRequest,
            'request_type',
            HelpRequest.REQUEST_TYPE_CHOICES
        )
        return Response(data)


class HelpRequestUrgencyStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    求助紧急程度统计
    """
    def get(self, request):
        data = build_choice_stats(
            HelpRequest,
            'urgency',
            HelpRequest.URGENCY_CHOICES
        )
        return Response(data)


class TaskStatusStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    志愿者任务状态统计
    """
    def get(self, request):
        data = build_choice_stats(
            VolunteerTask,
            'status',
            VolunteerTask.STATUS_CHOICES
        )
        return Response(data)


class WarningLevelStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    预警等级统计
    """
    def get(self, request):
        data = build_choice_stats(
            Warning,
            'level',
            Warning.LEVEL_CHOICES
        )
        return Response(data)


class WarningTypeStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    预警类型统计
    """
    def get(self, request):
        data = build_choice_stats(
            Warning,
            'warning_type',
            Warning.WARNING_TYPE_CHOICES
        )
        return Response(data)


class MaterialStockStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    物资库存统计
    """
    def get(self, request):
        materials = Material.objects.all().order_by('quantity', 'name')

        data = []
        for item in materials:
            data.append({
                'id': item.id,
                'name': item.name,
                'category': item.category,
                'quantity': item.quantity,
                'unit': item.unit,
                'warning_quantity': item.warning_quantity,
                'is_low_stock': item.quantity <= item.warning_quantity,
                'storage_location': item.storage_location,
                'expire_date': item.expire_date,
                'days_until_expire': (item.expire_date - timezone.now().date()).days if item.expire_date else None,
            })

        return Response(data)


class DailyHelpRequestStatsAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    近 7 日求助趋势
    """
    def get(self, request):
        today = timezone.now().date()
        result = []

        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = HelpRequest.objects.filter(
                created_at__date=day
            ).count()

            result.append({
                'date': day.strftime('%Y-%m-%d'),
                'label': day.strftime('%m-%d'),
                'count': count
            })

        return Response(result)

class HelpRequestMapDataAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    求助地理分布数据：为前端地图/散点图/热力图提供经纬度点位。
    """
    def get(self, request):
        urgency_weight_map = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4,
        }

        queryset = HelpRequest.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).select_related('resident').order_by('-created_at')[:500]

        data = []
        for item in queryset:
            data.append({
                'id': item.id,
                'resident_name': item.resident.username,
                'request_type': item.request_type,
                'request_type_display': item.get_request_type_display(),
                'urgency': item.urgency,
                'urgency_display': item.get_urgency_display(),
                'urgency_weight': urgency_weight_map.get(item.urgency, 1),
                'status': item.status,
                'status_display': item.get_status_display(),
                'description': item.description,
                'address': item.address,
                'latitude': float(item.latitude),
                'longitude': float(item.longitude),
                'created_at': item.created_at,
            })

        return Response(data)



def build_disaster_heat_count(help_request):
    """
    将求助紧急程度转换为热力强度。
    强度越高，前端热力图颜色越明显。
    """
    urgency_weight_map = {
        'low': 30,
        'medium': 55,
        'high': 80,
        'critical': 100,
    }

    status_decay_map = {
        'pending': 1.0,
        'assigned': 0.85,
        'processing': 0.7,
        'completed': 0.35,
        'cancelled': 0.2,
    }

    base = urgency_weight_map.get(help_request.urgency, 50)
    decay = status_decay_map.get(help_request.status, 1.0)
    return round(base * decay, 2)


class DisasterHeatmapAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    灾害/求助发生热力图数据。
    基于 HelpRequest 经纬度生成，紧急程度越高、越未处理，热力越强。
    """
    def get(self, request):
        queryset = HelpRequest.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).select_related('resident').order_by('-created_at')[:1000]

        data = []
        for item in queryset:
            data.append({
                'id': item.id,
                'longitude': float(item.longitude),
                'latitude': float(item.latitude),
                'count': build_disaster_heat_count(item),
                'resident_name': item.resident.username,
                'request_type': item.request_type,
                'request_type_display': item.get_request_type_display(),
                'urgency': item.urgency,
                'urgency_display': item.get_urgency_display(),
                'status': item.status,
                'status_display': item.get_status_display(),
                'address': item.address,
                'description': item.description,
                'created_at': item.created_at,
            })

        return Response(data)


class VolunteerHeatmapAPIView(APIView):
    permission_classes = [IsAdminRole]
    """
    志愿者位置热力图数据。
    基于 UserProfile 当前经纬度生成，可用志愿者热力更强。
    """
    def get(self, request):
        queryset = UserProfile.objects.filter(
            role='volunteer'
        ).exclude(
            current_latitude__isnull=True
        ).exclude(
            current_longitude__isnull=True
        ).select_related('user').order_by('-location_updated_at')[:1000]

        data = []
        for profile in queryset:
            data.append({
                'id': profile.id,
                'user_id': profile.user_id,
                'name': profile.user.username,
                'phone': profile.phone,
                'community': profile.community,
                'address': profile.address,
                'longitude': float(profile.current_longitude),
                'latitude': float(profile.current_latitude),
                'count': 85 if profile.is_available else 45,
                'is_available': profile.is_available,
                'location_updated_at': profile.location_updated_at,
            })

        return Response(data)


def build_command_help_request_item(item):
    task = getattr(item, 'volunteer_task', None)
    task_id = task.id if task else None
    task_status = task.status if task else None
    assigned_volunteer_id = task.volunteer_id if task else None
    assigned_volunteer_name = task.volunteer.username if task and task.volunteer else None

    # 可调度含义：该求助仍可由管理员派给志愿者。
    # 没有任务记录的 pending 求助可调度；已有“未绑定志愿者”的开放任务也可调度。
    is_open_unassigned_task = task is not None and task.volunteer_id is None and task.status in ['assigned', 'cancelled']
    is_dispatchable = (item.status == 'pending' and task is None) or is_open_unassigned_task

    return {
        'feature_type': 'help_request',
        'id': item.id,
        'resident_name': item.resident.username,
        'type': item.request_type,
        'type_display': item.get_request_type_display(),
        'urgency': item.urgency,
        'urgency_display': item.get_urgency_display(),
        'status': item.status,
        'status_display': item.get_status_display(),
        'summary': item.ai_summary,
        'description': item.description,
        'address': item.address,
        'longitude': float(item.longitude),
        'latitude': float(item.latitude),
        'created_at': item.created_at,
        'task_id': task_id,
        'task_status': task_status,
        'assigned_volunteer_id': assigned_volunteer_id,
        'assigned_volunteer_name': assigned_volunteer_name,
        'is_dispatchable': is_dispatchable,
    }


class CommandCenterAPIView(APIView):
    permission_classes = [IsAdminRole]
    """一图统管指挥舱数据：高危求助、志愿者、避难点统一输出。"""
    def get(self, request):
        help_requests = HelpRequest.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).select_related(
            'resident',
            'volunteer_task',
            'volunteer_task__volunteer',
        ).order_by('-created_at')[:300]

        volunteers = UserProfile.objects.filter(
            role='volunteer'
        ).exclude(
            current_latitude__isnull=True
        ).exclude(
            current_longitude__isnull=True
        ).select_related('user').order_by('-location_updated_at')[:300]

        shelters = Shelter.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).order_by('-is_available', 'name')[:300]

        return Response({
            'help_requests': [
                build_command_help_request_item(item) for item in help_requests
            ],
            'volunteers': [
                {
                    'feature_type': 'volunteer',
                    'id': item.user_id,
                    'profile_id': item.id,
                    'username': item.user.username,
                    'phone': item.phone,
                    'community': item.community,
                    'skills': item.skills,
                    'is_available': item.is_available,
                    'longitude': float(item.current_longitude),
                    'latitude': float(item.current_latitude),
                    'location_updated_at': item.location_updated_at,
                } for item in volunteers
            ],
            'shelters': [
                {
                    'feature_type': 'shelter',
                    'id': item.id,
                    'name': item.name,
                    'address': item.address,
                    'capacity': item.capacity,
                    'is_available': item.is_available,
                    'longitude': float(item.longitude),
                    'latitude': float(item.latitude),
                    'contact_phone': item.contact_phone,
                } for item in shelters
            ]
        })
