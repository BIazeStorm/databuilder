from rest_framework import viewsets, filters as drf_filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action


from .models import Brand, Shop, Product
from .serializers import BrandSerializer, ShopSerializer, ProductSerializer, AnalyticsRequestSerializer
from .filtersets import ProductFilter
from .services import AnalyticsService


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter, drf_filters.SearchFilter]


class BrandViewSet(BaseViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ["name"]
    ordering_fields = ["id", "name"]


class ShopViewSet(BaseViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    search_fields = ["name"]
    ordering_fields = ["id", "name"]


class ProductViewSet(BaseViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ["name"]
    ordering_fields = ["id", "name", "brand_id"]


class AnalyticsViewSet(BaseViewSet):
    @action(detail=False, methods=["post"], url_path="get-analytics")
    def get_analytics(self, request):
        serializer = AnalyticsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        params = serializer.validated_data

        service = AnalyticsService(
            dimensions=params.get("group_by"),
            metrics=params["metrics"],
        )

        current_range = params["date_range"]
        prev_range = params.get("prev_date_range")

        if prev_range:
            df = service.get_comparison_dataframe(
                current_range,
                prev_range,
            )
        else:
            df = service.get_dataframe(current_range["from"], current_range["to"])

        return Response(df.to_dict(orient="records"))
