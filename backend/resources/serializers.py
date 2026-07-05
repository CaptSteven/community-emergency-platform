from django.utils import timezone
from rest_framework import serializers
from .models import Shelter, Material


def validate_phone(value):
    if not value:
        return value
    digits = value.replace('-', '').replace(' ', '')
    if not digits.isdigit() or len(digits) < 7 or len(digits) > 20:
        raise serializers.ValidationError('联系电话格式不正确')
    return value


class ShelterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shelter
        fields = '__all__'

    def validate_contact_phone(self, value):
        return validate_phone(value)

    def validate(self, attrs):
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')

        if latitude is not None and not (-90 <= float(latitude) <= 90):
            raise serializers.ValidationError({'latitude': '纬度必须在 -90 到 90 之间'})

        if longitude is not None and not (-180 <= float(longitude) <= 180):
            raise serializers.ValidationError({'longitude': '经度必须在 -180 到 180 之间'})

        if (latitude is None) ^ (longitude is None):
            raise serializers.ValidationError('经度和纬度必须同时填写')

        capacity = attrs.get('capacity')
        if capacity is not None and capacity < 0:
            raise serializers.ValidationError({'capacity': '避难点容量不能为负数'})

        return attrs


class MaterialSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()
    days_until_expire = serializers.SerializerMethodField()
    is_expiring_soon = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    lifecycle_status = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = '__all__'

    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.warning_quantity

    def get_days_until_expire(self, obj):
        if not obj.expire_date:
            return None
        return (obj.expire_date - timezone.now().date()).days

    def get_is_expired(self, obj):
        days = self.get_days_until_expire(obj)
        return days is not None and days < 0

    def get_is_expiring_soon(self, obj):
        days = self.get_days_until_expire(obj)
        return days is not None and 0 <= days <= obj.expiry_warning_days

    def get_lifecycle_status(self, obj):
        if self.get_is_expired(obj):
            return '已过期'
        if self.get_is_expiring_soon(obj):
            return '临期'
        if obj.expire_date:
            return '正常'
        return '未登记'

    def validate(self, attrs):
        quantity = attrs.get('quantity')
        warning_quantity = attrs.get('warning_quantity')
        expiry_warning_days = attrs.get('expiry_warning_days')
        production_date = attrs.get('production_date')
        expire_date = attrs.get('expire_date')

        if quantity is not None and quantity < 0:
            raise serializers.ValidationError({'quantity': '库存数量不能为负数'})

        if warning_quantity is not None and warning_quantity < 0:
            raise serializers.ValidationError({'warning_quantity': '库存预警阈值不能为负数'})

        if expiry_warning_days is not None and expiry_warning_days < 0:
            raise serializers.ValidationError({'expiry_warning_days': '临期预警天数不能为负数'})

        if production_date and expire_date and expire_date < production_date:
            raise serializers.ValidationError({'expire_date': '过期日期不能早于生产日期'})

        return attrs
