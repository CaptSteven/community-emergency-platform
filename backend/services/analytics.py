from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ServiceType, ServiceSubscription, ServiceVisit


def _week_range(today):
    start = today - timedelta(days=today.weekday())  # 本周一
    end = start + timedelta(days=6)                   # 本周日
    return start, end


class ServiceOverviewAPIView(APIView):
    """社区服务总览：计划、覆盖人群、本周工单与完成情况。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        week_start, week_end = _week_range(today)

        active_subs = ServiceSubscription.objects.filter(is_active=True)
        week_visits = ServiceVisit.objects.filter(
            scheduled_date__gte=week_start, scheduled_date__lte=week_end
        )
        return Response({
            'active_subscriptions': active_subs.count(),
            'covered_residents': active_subs.values('resident').distinct().count(),
            'service_types': ServiceType.objects.filter(is_active=True).count(),
            'visits_total': ServiceVisit.objects.count(),
            'visits_completed': ServiceVisit.objects.filter(status='completed').count(),
            'visits_this_week': week_visits.count(),
            'completed_this_week': week_visits.filter(status='completed').count(),
            'pending_visits': ServiceVisit.objects.filter(
                status__in=['assigned', 'processing']
            ).count(),
            'unassigned_visits': ServiceVisit.objects.filter(
                status='assigned', volunteer__isnull=True
            ).count(),
        })


class ServiceTypeStatsAPIView(APIView):
    """各服务类型的工单量与完成量（用于图表）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = ServiceType.objects.annotate(
            total=Count('visits'),
            completed=Count('visits', filter=Q(visits__status='completed')),
        ).values('name', 'icon', 'total', 'completed')
        return Response(list(rows))


class VolunteerServiceLoadAPIView(APIView):
    """志愿者上门服务负载排行（完成 / 总量）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = (
            ServiceVisit.objects.filter(volunteer__isnull=False)
            .values('volunteer__username')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='completed')),
            )
            .order_by('-total')[:20]
        )
        return Response([
            {
                'volunteer': r['volunteer__username'],
                'total': r['total'],
                'completed': r['completed'],
            }
            for r in rows
        ])
