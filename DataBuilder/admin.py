from django.contrib import admin
from .models import Brand, Shop, Product, Receipt, CartItem


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "brand")
    list_filter = ("brand",)
    search_fields = ("name", "brand__name")
    autocomplete_fields = ("brand",)
    ordering = ("name",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "shop", "datetime", "total_price", "margin_price_total", "refund")
    list_filter = ("refund", "shop", "datetime")
    search_fields = ("id", "shop__name")
    autocomplete_fields = ("shop",)
    date_hierarchy = "datetime"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "receipt",
        "product",
        "qty",
        "price",
        "original_price",
        "total_price",
        "margin_price_total",
        "datetime",
    )
    list_filter = ("datetime", "receipt__shop")
    search_fields = ("receipt__id", "product__name")
    autocomplete_fields = ("receipt", "product")
    date_hierarchy = "datetime"
