from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from emergency_backend.permissions import IsAdminRole

from .models import UserProfile
from .serializers import (
    UserRegisterSerializer,
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
        serializer = UserRegisterSerializer(data=request.data)

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

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserListSerializer
    permission_classes = [IsAdminRole]

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
