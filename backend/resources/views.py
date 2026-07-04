from rest_framework import viewsets
from .models import Shelter, Material
from .serializers import ShelterSerializer, MaterialSerializer


class ShelterViewSet(viewsets.ModelViewSet):
    queryset = Shelter.objects.all()
    serializer_class = ShelterSerializer
    filterset_fields = ['is_available']
    search_fields = ['name', 'address']


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    filterset_fields = ['category']
    search_fields = ['name', 'category', 'storage_location']