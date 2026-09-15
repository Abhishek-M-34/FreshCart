from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    expiry_days = models.PositiveIntegerField(default=0) 
    lead_time_days = models.PositiveIntegerField(default=1)   
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_available_stock(self):
        today = timezone.localdate()

        batches = self.stock_batches.filter(
            quantity_remaining__gt=0
        )

        total = 0

        for batch in batches:
            if batch.expiry_date is None:
                total += batch.quantity_remaining
            elif batch.expiry_date >= today:
                total += batch.quantity_remaining

        return total

class StockBatch(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_batches"
    )
    quantity_received = models.PositiveIntegerField()
    quantity_remaining = models.PositiveIntegerField()
    arrival_date = models.DateField()
    expiry_date = models.DateField(
    null=True,
    blank=True
)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.arrival_date}"
        )
    def get_days_until_expiry(self):
        if self.expiry_date is None:
            return None

        return (self.expiry_date - timezone.localdate()).days


    def get_discount_percentage(self, expected_demand=0):
        days_until_expiry = self.get_days_until_expiry()

        # No expiry configured
        if days_until_expiry is None:
            return 0

        # Do not sell expired stock
        if days_until_expiry < 0:
            return 0

        # No excess stock
        excess_stock = self.quantity_remaining - expected_demand

        if excess_stock <= 0:
            return 0

        # Higher discount as expiry approaches
        if days_until_expiry <= 1:
            return 30

        if days_until_expiry <= 2:
            return 20

        if days_until_expiry <= 3:
            return 10

        return 0


    def get_discounted_price(self, expected_demand=0):
        discount_percentage = self.get_discount_percentage(
            expected_demand
        )

        return self.product.price * (
            1 - discount_percentage / 100
        )