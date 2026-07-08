from rest_framework import serializers

from .models import ServiceType, ServiceSubscription, ServiceVisit


class ServiceTypeSerializer(serializers.ModelSerializer):
    default_frequency_display = serializers.CharField(
        source='get_default_frequency_display', read_only=True
    )
    service_mode_display = serializers.CharField(
        source='get_service_mode_display', read_only=True
    )

    class Meta:
        model = ServiceType
        fields = [
            'id', 'name', 'code', 'category', 'description', 'required_skill',
            'default_frequency', 'default_frequency_display',
            'service_mode', 'service_mode_display', 'duration_minutes',
            'needs_health_record', 'icon', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']


class ServiceSubscriptionSerializer(serializers.ModelSerializer):
    resident_name = serializers.CharField(source='resident.username', read_only=True)
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    service_type_icon = serializers.CharField(source='service_type.icon', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    preferred_weekday_display = serializers.CharField(
        source='get_preferred_weekday_display', read_only=True
    )
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    rotation_group = serializers.SerializerMethodField()
    preferred_slot_display = serializers.SerializerMethodField()

    def get_preferred_slot_display(self, obj):
        return '' if obj.preferred_slot is None else obj.get_preferred_slot_display()

    class Meta:
        model = ServiceSubscription
        fields = [
            'id', 'resident', 'resident_name', 'service_type', 'service_type_name',
            'service_type_icon', 'frequency', 'frequency_display', 'preferred_weekday',
            'preferred_weekday_display', 'preferred_slot', 'preferred_slot_display',
            'address', 'latitude', 'longitude',
            'note', 'is_active', 'start_date', 'last_generated_date',
            'rotation_index', 'rotation_group',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['last_generated_date', 'rotation_index', 'created_by', 'created_at']
        # resident 由视图层注入：居民自动取本人，管理员需显式指定（在 perform_create 校验）
        extra_kwargs = {'resident': {'required': False}}

    def get_rotation_group(self, obj):
        """返回循环组成员及当前进行到谁，供 web/App 展示轮换进度。"""
        ids = list(obj.rotation_volunteers or [])
        if not ids:
            return []
        from django.contrib.auth.models import User
        name_map = {u.id: u.username for u in User.objects.filter(id__in=ids)}
        cur = obj.rotation_index % len(ids)
        return [
            {'id': vid, 'username': name_map.get(vid, f'#{vid}'),
             'order': i + 1, 'is_next': i == cur}
            for i, vid in enumerate(ids)
        ]


class ServiceVisitSerializer(serializers.ModelSerializer):
    resident_name = serializers.CharField(source='resident.username', read_only=True)
    # volunteer 可为空（单次任务待派单）：source 链遇 None 会整键跳过，前端拿到 undefined，
    # 故用 MethodField 恒定返回字符串
    volunteer_name = serializers.SerializerMethodField()
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    service_type_icon = serializers.CharField(source='service_type.icon', read_only=True)
    needs_health_record = serializers.BooleanField(
        source='service_type.needs_health_record', read_only=True
    )
    status_display = serializers.SerializerMethodField()

    def get_volunteer_name(self, obj):
        return obj.volunteer.username if obj.volunteer_id else ''

    def get_status_display(self, obj):
        # 已排班但还没有志愿者 = 等管理员派单，展示为「待派单」而非误导性的「已排班」
        if obj.status == 'assigned' and obj.volunteer_id is None:
            return '待派单'
        return obj.get_status_display()

    slot_display = serializers.SerializerMethodField()

    def get_slot_display(self, obj):
        return '' if obj.scheduled_slot is None else obj.get_scheduled_slot_display()

    class Meta:
        model = ServiceVisit
        fields = [
            'id', 'subscription', 'service_type', 'service_type_name', 'service_type_icon',
            'needs_health_record', 'resident', 'resident_name', 'volunteer', 'volunteer_name',
            'scheduled_date', 'scheduled_slot', 'slot_display',
            'status', 'status_display', 'address', 'latitude', 'longitude',
            'note', 'duration_minutes', 'feedback', 'completion_photo', 'confirm_photo',
            'checkin_photo', 'checkin_distance_m', 'checkin_remote', 'checkin_at',
            'systolic', 'diastolic', 'heart_rate', 'temperature', 'health_note',
            'started_at', 'completed_at', 'confirmed_at', 'created_at',
        ]
        read_only_fields = [
            'service_type', 'resident', 'volunteer', 'status', 'completion_photo', 'confirm_photo',
            'checkin_photo', 'checkin_distance_m', 'checkin_remote', 'checkin_at',
            'started_at', 'completed_at', 'confirmed_at', 'created_at',
        ]
