from rest_framework import viewsets, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.request import Request
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
    def get_analytics(self, request: Request) -> Response:
        serializer = AnalyticsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        params = serializer.validated_data

        group_by = params.get("group_by", [])
        metrics = params.get("metrics", [])
        include_total = params.get("total", False)

        service = AnalyticsService(
            dimensions=group_by,
            metrics=metrics,
        )

        current_range = params["date_range"]
        prev_range = params.get("prev_date_range")

        if prev_range:
            df = service.get_comparison_dataframe(
                current_range,
                prev_range,
            )
        else:
            df = service.get_dataframe(current_range["from_date"], current_range["to_date"])

        response_payload = {}

        if not group_by:
            return Response({"data": df.to_dict(orient="records")})

        if include_total:
            if prev_range:
                total_df = service.get_comparison_dataframe(current_range, prev_range, as_total=True)
            else:
                total_df = service.get_dataframe(current_range["from_date"], current_range["to_date"], as_total=True)

            if not total_df.empty:
                response_payload["total"] = total_df.to_dict(orient="records")[0]
            else:
                response_payload["total"] = {}

        response_payload["data"] = df.to_dict(orient="records")

        return Response(response_payload)
