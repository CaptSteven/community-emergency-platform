from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'role',
            'role_display',
            'phone',
            'community',
            'address',
            'is_available',
        ]


class UserRegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    community = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'password',
            'email',
            'role',
            'phone',
            'community',
            'address',
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def create(self, validated_data):
        role = validated_data.pop('role')
        phone = validated_data.pop('phone', '')
        community = validated_data.pop('community', '')
        address = validated_data.pop('address', '')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            username=validated_data.get('username'),
            email=validated_data.get('email', ''),
            password=password
        )

        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone,
            community=community,
            address=address
        )

        return user


class UserInfoSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'profile',
        ]
class UserListSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)
    role_display = serializers.CharField(source='profile.get_role_display', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    community = serializers.CharField(source='profile.community', read_only=True)
    address = serializers.CharField(source='profile.address', read_only=True)
    is_available = serializers.BooleanField(source='profile.is_available', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'role_display',
            'phone',
            'community',
            'address',
            'is_available',
        ]