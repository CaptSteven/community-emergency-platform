from rest_framework import serializers
from .models import Shelter, Material


class ShelterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shelter
        fields = '__all__'


class MaterialSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = '__all__'

    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.warning_quantity