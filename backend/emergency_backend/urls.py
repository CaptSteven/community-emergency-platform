from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from users.views import RegisterAPIView, LoginAPIView, MeAPIView, UserViewSet, UpdateMyLocationAPIView, EmergencyHelpAPIView, DeviceTokenAPIView
from alerts.views import WarningViewSet
from requests_app.views import HelpRequestViewSet
from tasks.views import VolunteerTaskViewSet
from resources.views import ShelterViewSet, MaterialViewSet
from analytics.views import (
    OverviewAPIView,
    HelpRequestStatusStatsAPIView,
    HelpRequestTypeStatsAPIView,
    HelpRequestUrgencyStatsAPIView,
    TaskStatusStatsAPIView,
    WarningLevelStatsAPIView,
    WarningTypeStatsAPIView,
    MaterialStockStatsAPIView,
    DailyHelpRequestStatsAPIView,
    HelpRequestMapDataAPIView,
    DisasterHeatmapAPIView,
    VolunteerHeatmapAPIView,
    CommandCenterAPIView,
)
from notifications.views import NotificationViewSet



def home(request):
    return JsonResponse({
        'message': '社区应急互助与灾害预警平台后端服务运行成功',
        'admin': '/admin/',
        'api': '/api/',
        'warnings': '/api/warnings/',
        'help_requests': '/api/help-requests/',
        'tasks': '/api/tasks/',
        'shelters': '/api/shelters/',
        'materials': '/api/materials/',
        'analytics': '/api/analytics/overview/',
    }, json_dumps_params={'ensure_ascii': False})


router = DefaultRouter()
router.register(r'warnings', WarningViewSet)
router.register(r'help-requests', HelpRequestViewSet)
router.register(r'tasks', VolunteerTaskViewSet)
router.register(r'shelters', ShelterViewSet)
router.register(r'materials', MaterialViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'users', UserViewSet)



urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/analytics/overview/', OverviewAPIView.as_view()),
    path('api/analytics/help-request-status/', HelpRequestStatusStatsAPIView.as_view()),
    path('api/analytics/help-request-types/', HelpRequestTypeStatsAPIView.as_view()),
    path('api/analytics/help-request-urgency/', HelpRequestUrgencyStatsAPIView.as_view()),
    path('api/analytics/task-status/', TaskStatusStatsAPIView.as_view()),
    path('api/analytics/warning-levels/', WarningLevelStatsAPIView.as_view()),
    path('api/analytics/warning-types/', WarningTypeStatsAPIView.as_view()),
    path('api/analytics/material-stock/', MaterialStockStatsAPIView.as_view()),
    path('api/analytics/daily-requests/', DailyHelpRequestStatsAPIView.as_view()),
    path('api/analytics/help-request-map/', HelpRequestMapDataAPIView.as_view()),
    path('api/analytics/disaster-heatmap/', DisasterHeatmapAPIView.as_view()),
    path('api/analytics/volunteer-heatmap/', VolunteerHeatmapAPIView.as_view()),
    path('api/analytics/command-center/', CommandCenterAPIView.as_view()),
    path('api/auth/register/', RegisterAPIView.as_view()),
    path('api/auth/login/', LoginAPIView.as_view()),
    path('api/auth/me/', MeAPIView.as_view()),
    path('api/auth/update-location/', UpdateMyLocationAPIView.as_view()),
    path('api/auth/emergency/', EmergencyHelpAPIView.as_view()),
    path('api/auth/device-token/', DeviceTokenAPIView.as_view()),
]
