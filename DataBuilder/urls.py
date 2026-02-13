from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from .viewsets import BrandViewSet, ProductViewSet, ShopViewSet, AnalyticsViewSet

router = DefaultRouter()
router.register(r"brands", BrandViewSet)
router.register(r"shops", ShopViewSet)
router.register(r"products", ProductViewSet)
router.register(r"analytics", AnalyticsViewSet, basename="analytics")

urlpatterns = [
    path("api/", include(router.urls)),
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
]
