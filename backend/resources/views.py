from rest_framework import viewsets
from emergency_backend.permissions import IsAdminOrReadOnly
from .models import Shelter, Material
from .serializers import ShelterSerializer, MaterialSerializer


class ShelterViewSet(viewsets.ModelViewSet):
    queryset = Shelter.objects.all()
    serializer_class = ShelterSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['is_available']
    search_fields = ['name', 'address']


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['category']
    search_fields = ['name', 'category', 'storage_location']