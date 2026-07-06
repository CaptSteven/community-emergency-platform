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
    monthly_cancel_count = serializers.SerializerMethodField()

    def get_monthly_cancel_count(self, obj):
        from tasks.models import TaskCancellation
        from django.utils import timezone
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return TaskCancellation.objects.filter(volunteer=obj, created_at__gte=month_start).count()

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
            'monthly_cancel_count',
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


class UserAdminSerializer(serializers.ModelSerializer):
    """管理员用户管理：创建/编辑用户与角色（志愿者账号仅此处开通）。"""
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    phone = serializers.CharField(required=False, allow_blank=True)
    community = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    skills = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6, required=False, allow_blank=True)
    role_display = serializers.CharField(source='profile.get_role_display', read_only=True)
    is_available = serializers.BooleanField(source='profile.is_available', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'password', 'email',
            'role', 'role_display', 'phone', 'community', 'address', 'skills', 'is_available',
        ]

    def to_representation(self, instance):
        # 输出统一走 UserListSerializer，避免写入字段(role/phone 等)在输出时找不到 User 属性
        return UserListSerializer(instance, context=self.context).to_representation(instance)

    def validate_username(self, value):
        qs = User.objects.filter(username=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def create(self, validated_data):
        role = validated_data.pop('role')
        phone = validated_data.pop('phone', '')
        community = validated_data.pop('community', '')
        address = validated_data.pop('address', '')
        skills = validated_data.pop('skills', '')
        password = validated_data.pop('password', '')
        if not password:
            raise serializers.ValidationError({'password': '新建用户必须设置密码'})
        user = User.objects.create_user(
            username=validated_data.get('username'),
            email=validated_data.get('email', ''),
            password=password,
        )
        UserProfile.objects.create(
            user=user, role=role, phone=phone,
            community=community, address=address, skills=skills,
        )
        return user

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password', '')
        profile = getattr(instance, 'profile', None)
        for field in ['phone', 'community', 'address', 'skills']:
            if field in validated_data and profile is not None:
                setattr(profile, field, validated_data.pop(field))
        if 'username' in validated_data:
            instance.username = validated_data['username']
        instance.email = validated_data.get('email', instance.email)
        if password:
            instance.set_password(password)
        instance.save()
        if profile is not None:
            if role is not None:
                profile.role = role
            profile.save()
        return instance
