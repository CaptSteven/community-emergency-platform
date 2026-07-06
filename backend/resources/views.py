import math
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from emergency_backend.permissions import IsAdminOrReadOnly
from .models import Shelter, Material
from .serializers import ShelterSerializer, MaterialSerializer


def haversine_km(lng1, lat1, lng2, lat2):
    if None in [lng1, lat1, lng2, lat2]:
        return None
    lng1, lat1, lng2, lat2 = map(math.radians, [float(lng1), float(lat1), float(lng2), float(lat2)])
    dlng = lng2 - lng1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return round(6371.0088 * c, 2)


class ShelterViewSet(viewsets.ModelViewSet):
    queryset = Shelter.objects.all().order_by('-created_at')
    serializer_class = ShelterSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['is_available']
    search_fields = ['name', 'address', 'contact_phone']
    ordering_fields = ['created_at', 'capacity', 'name']

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """根据经纬度返回附近可用避难点，供鸿蒙端 /shelters/nearby/ 调用。"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        limit = request.query_params.get('limit', 10)

        try:
            lat_value = float(lat)
            lng_value = float(lng)
            limit_value = min(max(int(limit), 1), 50)
        except (TypeError, ValueError):
            return Response({'message': '请提供合法的 lat、lng 和 limit 参数'}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= lat_value <= 90):
            return Response({'message': '纬度必须在 -90 到 90 之间'}, status=status.HTTP_400_BAD_REQUEST)
        if not (-180 <= lng_value <= 180):
            return Response({'message': '经度必须在 -180 到 180 之间'}, status=status.HTTP_400_BAD_REQUEST)

        shelters = Shelter.objects.filter(
            is_available=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        data = []
        for shelter in shelters:
            item = ShelterSerializer(shelter).data
            item['distance_km'] = haversine_km(lng_value, lat_value, shelter.longitude, shelter.latitude)
            data.append(item)

        data.sort(key=lambda item: item['distance_km'] if item['distance_km'] is not None else 10**9)
        return Response(data[:limit_value])


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all().order_by('-updated_at')
    serializer_class = MaterialSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['category']
    search_fields = ['name', 'category', 'storage_location']
    ordering_fields = ['updated_at', 'quantity', 'expire_date', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        stock_status = self.request.query_params.get('stock_status')
        expiry_status = self.request.query_params.get('expiry_status')
        today = timezone.now().date()

        if stock_status == 'low':
            queryset = queryset.filter(quantity__lte=F('warning_quantity'))
        elif stock_status == 'normal':
            queryset = queryset.filter(quantity__gt=F('warning_quantity'))

        if expiry_status == 'expired':
            queryset = queryset.filter(expire_date__lt=today)
        elif expiry_status == 'soon':
            # MySQL/SQLite 都能安全执行的朴素过滤：先筛选有过期日期且未过期，再在 Python 端做二次筛选。
            ids = [
                item.id for item in queryset.exclude(expire_date__isnull=True).filter(expire_date__gte=today)
                if (item.expire_date - today).days <= item.expiry_warning_days
            ]
            queryset = queryset.filter(id__in=ids)
        elif expiry_status == 'normal':
            ids = [
                item.id for item in queryset.exclude(expire_date__isnull=True).filter(expire_date__gte=today)
                if (item.expire_date - today).days > item.expiry_warning_days
            ]
            queryset = queryset.filter(Q(id__in=ids) | Q(expire_date__isnull=True))

        return queryset
