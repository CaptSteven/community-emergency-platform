from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from emergency_backend.permissions import IsAdminRole

from .models import UserProfile
from requests_app.models import HelpRequest
from notifications.utils import create_notification
from .serializers import (
    UserRegisterSerializer,
    UserAdminSerializer,
    UserInfoSerializer,
    UserListSerializer,
    UserLocationUpdateSerializer,
)
def build_user_response(user, token=None):
    profile = getattr(user, 'profile', None)

    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': profile.role if profile else None,
        'role_display': profile.get_role_display() if profile else None,
        'phone': profile.phone if profile else None,
        'community': profile.community if profile else None,
        'address': profile.address if profile else None,
        'skills': profile.skills if profile else None,
        'current_latitude': profile.current_latitude if profile else None,
        'current_longitude': profile.current_longitude if profile else None,
        'location_updated_at': profile.location_updated_at if profile else None,
        'is_available': profile.is_available if profile else None,
    }

    if token:
        data = {
            'token': token.key,
            'user': data
        }

    return data


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.copy()
        data['role'] = 'resident'  # 自助注册仅限居民；志愿者账号由管理员线下开通
        serializer = UserRegisterSerializer(data=data)

        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'message': '注册成功',
                'token': token.key,
                'user': build_user_response(user)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'message': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({
                'message': '用户名或密码错误'
            }, status=status.HTTP_400_BAD_REQUEST)

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'message': '登录成功',
            'token': token.key,
            'user': build_user_response(user)
        })


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'user': build_user_response(request.user)
        })

class EmergencyHelpAPIView(APIView):
    """未登录一键 SOS 求助接口。

    鸿蒙端登录页会调用 /api/auth/emergency/，只上报经纬度。
    后端为匿名 SOS 建立一个系统居民账号，并生成紧急求助单，避免接口 404 或因没有 resident 外键而失败。
    """
    permission_classes = [AllowAny]

    def post(self, request):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if latitude is None or longitude is None:
            return Response({'message': '一键求助需要上报当前位置'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latitude_value = float(latitude)
            longitude_value = float(longitude)
        except (TypeError, ValueError):
            return Response({'message': '经纬度格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= latitude_value <= 90):
            return Response({'message': '纬度必须在 -90 到 90 之间'}, status=status.HTTP_400_BAD_REQUEST)
        if not (-180 <= longitude_value <= 180):
            return Response({'message': '经度必须在 -180 到 180 之间'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            sos_user, _ = User.objects.get_or_create(
                username='sos_emergency',
                defaults={'email': 'sos@example.local'}
            )
            if not sos_user.has_usable_password():
                # 已经是不可登录账号时保持不变；新建账号也设置为不可登录，避免被普通登录使用。
                pass
            else:
                sos_user.set_unusable_password()
                sos_user.save(update_fields=['password'])

            UserProfile.objects.get_or_create(
                user=sos_user,
                defaults={
                    'role': 'resident',
                    'phone': '',
                    'community': '系统一键求助',
                    'address': '未登录用户 SOS 上报位置',
                }
            )

            help_request = HelpRequest.objects.create(
                resident=sos_user,
                request_type='other',
                urgency='critical',
                description='未登录用户通过鸿蒙端一键 SOS 发起紧急求助，请管理员立即联系现场或根据定位安排救援。',
                address=request.data.get('address') or '一键 SOS 定位上报位置',
                latitude=latitude_value,
                longitude=longitude_value,
                status='pending',
            )

            admins = User.objects.filter(Q(profile__role='admin') | Q(is_superuser=True)).distinct()
            for admin in admins:
                create_notification(
                    recipient=admin,
                    title='一键 SOS 紧急求助',
                    content=f'收到未登录用户一键 SOS：经度 {longitude_value:.6f}，纬度 {latitude_value:.6f}，请立即处理。',
                    category='help_request',
                    related_type='help_request',
                    related_id=help_request.id
                )

        return Response({
            'message': '紧急求助已发送',
            'help_request_id': help_request.id,
            'status': help_request.status,
        }, status=status.HTTP_201_CREATED)


class DeviceTokenAPIView(APIView):
    """鸿蒙端设备推送 Token 上报接口。

    当前项目主要实现站内通知；该接口先保证端侧调用不会 404。后续若接入 Push Kit 服务端推送，
    可以在这里将 push_token 持久化到单独的 DeviceToken 表。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        push_token = request.data.get('push_token')
        platform = request.data.get('platform', 'harmony')

        if not push_token:
            return Response({'message': 'push_token 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': '设备令牌已接收',
            'platform': platform,
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserListSerializer
    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserAdminSerializer
        return UserListSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_superuser:
            return Response({'message': '不能删除超级管理员'}, status=status.HTTP_400_BAD_REQUEST)
        if instance == request.user:
            return Response({'message': '不能删除当前登录账号'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)

        # 只有管理员或超级管理员可以查看用户列表
        if not user.is_superuser:
            if profile is None or profile.role != 'admin':
                return User.objects.none()

        queryset = User.objects.all().select_related('profile')

        role = self.request.query_params.get('role')
        is_available = self.request.query_params.get('is_available')
        search = self.request.query_params.get('search')

        if role:
            queryset = queryset.filter(profile__role=role)

        if is_available == 'true':
            queryset = queryset.filter(profile__is_available=True)
        elif is_available == 'false':
            queryset = queryset.filter(profile__is_available=False)

        if search:
            queryset = queryset.filter(
                username__icontains=search
            )

        return queryset.order_by('id')

class UpdateMyLocationAPIView(APIView):
    """
    当前登录用户上报实时位置。
    志愿者鸿蒙端后续可以调用该接口，将当前位置写入 UserProfile，供数据大屏热力图使用。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, 'profile', None)
        if profile is None:
            return Response({'message': '当前用户没有资料信息'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserLocationUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(location_updated_at=timezone.now())

        return Response({
            'message': '位置更新成功',
            'current_latitude': profile.current_latitude,
            'current_longitude': profile.current_longitude,
            'location_updated_at': profile.location_updated_at,
        })
