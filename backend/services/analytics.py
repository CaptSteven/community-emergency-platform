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
                status__in=['assigned', 'processing', 'pending_confirm']
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


class UpcomingVisitsAPIView(APIView):
    """未来 7 天（含今天）即将上门、尚未完成的服务工单（只读，按日期升序）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        end = today + timedelta(days=7)
        qs = (
            ServiceVisit.objects.filter(
                scheduled_date__gte=today, scheduled_date__lte=end,
                status__in=['assigned', 'processing'],
            )
            .select_related('resident', 'volunteer', 'service_type')
            .order_by('scheduled_date', 'created_at')
        )
        visits = [
            {
                'id': v.id,
                'scheduled_date': v.scheduled_date,
                'service_type': v.service_type.name,
                'icon': v.service_type.icon,
                'resident': v.resident.username,
                'volunteer': v.volunteer.username if v.volunteer else None,
                'status': v.status,
                'status_display': v.get_status_display(),
                'address': v.address,
            }
            for v in qs
        ]
        return Response({
            'range_start': today,
            'range_end': end,
            'count': len(visits),
            'visits': visits,
        })


class VolunteerLeaderboardAPIView(APIView):
    """志愿积分排行榜：按积分排序，含总/本周服务时长与完成单数。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth.models import User
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        rows = []
        vols = User.objects.filter(is_active=True, profile__role='volunteer').select_related('profile')
        for u in vols:
            completed = ServiceVisit.objects.filter(volunteer=u, status='completed')
            total_min = sum(v.duration_minutes or 0 for v in completed)
            week_min = sum(v.duration_minutes or 0 for v in completed.filter(completed_at__date__gte=week_start))
            rows.append({
                'volunteer': u.username,
                'points': (u.profile.points if hasattr(u, 'profile') else 0) or 0,
                'total_minutes': total_min,
                'week_minutes': week_min,
                'completed_count': completed.count(),
            })
        rows.sort(key=lambda r: (-r['points'], -r['total_minutes']))
        for i, r in enumerate(rows):
            r['rank'] = i + 1
        return Response(rows[:50])


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
