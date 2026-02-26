from rest_framework import serializers
from .models import Brand, Shop, Product
from .validators import validate_comparison_metrics


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class DateRangeSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()


class AnalyticsRequestSerializer(serializers.Serializer):
    metrics = serializers.ListField(child=serializers.CharField())
    group_by = serializers.ListField(child=serializers.CharField())
    date_range = DateRangeSerializer()
    prev_date_range = DateRangeSerializer(required=False, allow_null=True)
    total = serializers.BooleanField(required=False, default=False)
    render_type = serializers.CharField(required=False, default="json")
    email = serializers.EmailField(required=False)

    def validate(self, data):
        if data.get("render_type") == "excel" and not data.get("email"):
            raise serializers.ValidationError({"email": "Для формату Excel необхідно вказати email."})
        return data

    validators = [validate_comparison_metrics]
