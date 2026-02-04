from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import BrandViewSet, ProductViewSet, ShopViewSet, AnalyticsViewSet

router = DefaultRouter()
router.register(r'brands', BrandViewSet)
router.register(r'shops', ShopViewSet)
router.register(r'products', ProductViewSet)
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('api/', include(router.urls)),
]