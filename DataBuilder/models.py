from django.db import models


class Brand(models.Model):
    name = models.CharField(max_length=100)


class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True)


class Shop(models.Model):
    name = models.CharField(max_length=100)


class Receipt(models.Model):
    datetime = models.DateTimeField()
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=4)
    margin_price_total = models.DecimalField(max_digits=10, decimal_places=4)
    refund = models.BooleanField(default=False)


class CartItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=4)
    original_price = models.DecimalField(max_digits=10, decimal_places=4)
    qty = models.DecimalField(max_digits=10, decimal_places=4)
    total_price = models.DecimalField(max_digits=10, decimal_places=5)
    margin_price_total = models.DecimalField(max_digits=10, decimal_places=5)
    datetime = models.DateTimeField()
