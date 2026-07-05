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