from django.db.models import F, Q
from django.utils import timezone
from rest_framework import viewsets
from emergency_backend.permissions import IsAdminOrReadOnly
from .models import Shelter, Material
from .serializers import ShelterSerializer, MaterialSerializer


class ShelterViewSet(viewsets.ModelViewSet):
    queryset = Shelter.objects.all().order_by('-created_at')
    serializer_class = ShelterSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['is_available']
    search_fields = ['name', 'address', 'contact_phone']
    ordering_fields = ['created_at', 'capacity', 'name']


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
