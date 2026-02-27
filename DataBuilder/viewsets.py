from typing import Union

from rest_framework import viewsets, filters as drf_filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse


from .models import Brand, Shop, Product
from .serializers import BrandSerializer, ShopSerializer, ProductSerializer, AnalyticsRequestSerializer
from .filtersets import ProductFilter
from .services import AnalyticsService
from .tasks import generate_and_send_excel_task, generate_and_send_chart_task


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
    def get_analytics(self, request: Request) -> Union[Response, HttpResponse]:
        serializer = AnalyticsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        params = serializer.validated_data
        render_type = params.get("render_type", "json")
        email = params.get("email")

        if render_type == "excel":
            generate_and_send_excel_task.delay(request.data)
            return Response(
                {"message": "Запит прийнято. Звіт формується та буде надіслано на пошту."},
                status=status.HTTP_202_ACCEPTED,
            )

        if render_type == "chart":
            if email:
                generate_and_send_chart_task.delay(request.data, email)
                return Response(
                    {"message": "Запит прийнято. Графік формується та буде надіслано на пошту."},
                    status=status.HTTP_202_ACCEPTED,
                )

            df = self._get_analytics_dataframe(params)

            service = AnalyticsService(
                dimensions=params.get("group_by", []),
                metrics=params.get("metrics", []),
            )
            chart_html = service.generate_plotly_chart(df, params.get("chart_type", "Bar Chart"))

            return HttpResponse(chart_html, content_type="text/html")

        df = self._get_analytics_dataframe(params)
        response_payload = {}
        group_by = params.get("group_by", [])
        include_total = params.get("total", False)

        if not group_by:
            return Response({"data": df.to_dict(orient="records")})

        if include_total:
            total_df = self._get_total_dataframe(params)
            response_payload["total"] = total_df.to_dict(orient="records")[0] if not total_df.empty else {}

        response_payload["data"] = df.to_dict(orient="records")
        return Response(response_payload)

    @staticmethod
    def _get_analytics_dataframe(params):
        service = AnalyticsService(
            dimensions=params.get("group_by", []),
            metrics=params.get("metrics", []),
        )
        current_range = params["date_range"]
        prev_range = params.get("prev_date_range")

        if prev_range:
            return service.get_comparison_dataframe(current_range, prev_range)
        return service.get_dataframe(current_range["from_date"], current_range["to_date"])

    @staticmethod
    def _get_total_dataframe(params):
        service = AnalyticsService(
            dimensions=params.get("group_by", []),
            metrics=params.get("metrics", []),
        )
        current_range = params["date_range"]
        prev_range = params.get("prev_date_range")

        if prev_range:
            return service.get_comparison_dataframe(current_range, prev_range, as_total=True)
        return service.get_dataframe(current_range["from_date"], current_range["to_date"], as_total=True)
