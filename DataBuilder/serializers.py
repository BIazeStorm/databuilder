from rest_framework import serializers
from .models import Brand, Shop, Product


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class AnalyticsRequestSerializer(serializers.Serializer):
    metrics = serializers.ListField(child=serializers.CharField())
    group_by = serializers.ListField(child=serializers.CharField())
    date_range = serializers.DictField(child=serializers.DateTimeField())
