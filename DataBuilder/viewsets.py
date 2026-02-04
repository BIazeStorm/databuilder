from rest_framework import viewsets, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Brand, Shop, Product
from .serializers import BrandSerializer, ShopSerializer, ProductSerializer
from .filtersets import ProductFilter


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter, drf_filters.SearchFilter]


class BrandViewSet(BaseViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class ShopViewSet(BaseViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class ProductViewSet(BaseViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'brand_id']
