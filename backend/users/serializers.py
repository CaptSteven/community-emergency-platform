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
            'skills',
            'current_latitude',
            'current_longitude',
            'location_updated_at',
            'is_available',
        ]


class UserRegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    community = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    skills = serializers.CharField(required=False, allow_blank=True)
    current_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    current_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
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
            'skills',
            'current_latitude',
            'current_longitude',
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate(self, attrs):
        lat = attrs.get('current_latitude')
        lng = attrs.get('current_longitude')
        if lat is not None and not (-90 <= float(lat) <= 90):
            raise serializers.ValidationError({'current_latitude': '纬度必须在 -90 到 90 之间'})
        if lng is not None and not (-180 <= float(lng) <= 180):
            raise serializers.ValidationError({'current_longitude': '经度必须在 -180 到 180 之间'})
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role')
        phone = validated_data.pop('phone', '')
        community = validated_data.pop('community', '')
        address = validated_data.pop('address', '')
        skills = validated_data.pop('skills', '')
        current_latitude = validated_data.pop('current_latitude', None)
        current_longitude = validated_data.pop('current_longitude', None)
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
            address=address,
            skills=skills,
            current_latitude=current_latitude,
            current_longitude=current_longitude
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
    skills = serializers.CharField(source='profile.skills', read_only=True)
    current_latitude = serializers.DecimalField(source='profile.current_latitude', max_digits=10, decimal_places=7, read_only=True)
    current_longitude = serializers.DecimalField(source='profile.current_longitude', max_digits=10, decimal_places=7, read_only=True)
    location_updated_at = serializers.DateTimeField(source='profile.location_updated_at', read_only=True)
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
            'skills',
            'current_latitude',
            'current_longitude',
            'location_updated_at',
            'is_available',
        ]


class UserLocationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'current_latitude',
            'current_longitude',
        ]

    def validate(self, attrs):
        latitude = attrs.get('current_latitude')
        longitude = attrs.get('current_longitude')

        if latitude is None or longitude is None:
            raise serializers.ValidationError('经纬度不能为空')

        if not (-90 <= float(latitude) <= 90):
            raise serializers.ValidationError('纬度必须在 -90 到 90 之间')

        if not (-180 <= float(longitude) <= 180):
            raise serializers.ValidationError('经度必须在 -180 到 180 之间')

        return attrs
