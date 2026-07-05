from django.contrib.auth import authenticate
from django.contrib.auth.models import User

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
        if role:
            queryset = queryset.filter(profile__role=role)

        return queryset