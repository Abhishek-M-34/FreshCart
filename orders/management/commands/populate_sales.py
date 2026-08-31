import random

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product


User = get_user_model()


class Command(BaseCommand):

    help = "Generate realistic historical sales data for FreshCart"

    def handle(self, *args, **kwargs):

        self.stdout.write(
            self.style.WARNING(
                "Generating FreshCart historical sales data..."
            )
        )

        # --------------------------------
        # Remove old demo customer orders
        # --------------------------------

        demo_user = User.objects.filter(
            username="demo_customer"
        ).first()

        if demo_user:

            Order.objects.filter(
                user=demo_user
            ).delete()

        else:

            demo_user = User.objects.create_user(
                username="demo_customer",
                email="demo@freshcart.com",
                password="demo123",
                first_name="Demo",
                last_name="Customer"
            )

        # --------------------------------
        # Get Products
        # --------------------------------

        products = list(
            Product.objects.all()
        )

        if not products:

            self.stdout.write(
                self.style.ERROR(
                    "No products found."
                )
            )

            self.stdout.write(
                "Please add products from the admin panel first."
            )

            return

        # --------------------------------
        # Product Demand Profiles
        # --------------------------------

        demand_profiles = {

            "tomato": 8,
            "potato": 7,
            "onion": 7,
            "carrot": 5,
            "apple": 5,
            "banana": 6,
            "mango": 4,
            "orange": 4,
            "cabbage": 4,
            "cauliflower": 3,
            "spinach": 3,
            "beans": 4,
        }

        # --------------------------------
        # Historical Period
        # --------------------------------

        today = timezone.now().date()

        start_date = (
            today - timedelta(days=30)
        )

        total_orders = 0

        total_revenue = Decimal("0.00")

        # --------------------------------
        # Generate daily sales
        # --------------------------------

        for day_number in range(31):

            sale_date = (
                start_date
                + timedelta(days=day_number)
            )

            # Weekend multiplier
            if sale_date.weekday() >= 5:
                weekend_multiplier = 1.25
            else:
                weekend_multiplier = 1.0

            # --------------------------------
            # Generate product demand
            # --------------------------------

            daily_products = []

            for product in products:

                product_key = (
                    product.name.lower()
                )

                base_demand = demand_profiles.get(
                    product_key,
                    4
                )

                demand = int(
                    base_demand
                    * weekend_multiplier
                    * random.uniform(
                        0.7,
                        1.3
                    )
                )

                demand = max(
                    demand,
                    1
                )

                daily_products.append(
                    {
                        "product": product,
                        "quantity": demand
                    }
                )

            # --------------------------------
            # Convert product demand
            # into customer orders
            # --------------------------------

            remaining_products = daily_products.copy()

            while remaining_products:

                # Select 1–4 products per order
                number_of_products = min(
                    random.randint(1, 4),
                    len(remaining_products)
                )

                selected = random.sample(
                    remaining_products,
                    number_of_products
                )

                order = Order.objects.create(

                    user=demo_user,

                    total_amount=Decimal("0.00"),

                    status="delivered",

                    shipping_address=(
                        "FreshCart Demo Address, "
                        "Kerala, India"
                    )
                )

                order_total = Decimal("0.00")

                for item in selected:

                    product = item["product"]

                    available_quantity = item[
                        "quantity"
                    ]

                    quantity = random.randint(
                        1,
                        max(
                            1,
                            min(
                                available_quantity,
                                4
                            )
                        )
                    )

                    item["quantity"] -= quantity

                    price = product.price

                    item_total = (
                        price * quantity
                    )

                    OrderItem.objects.create(

                        order=order,

                        product=product,

                        product_name=product.name,

                        price=price,

                        quantity=quantity
                    )

                    order_total += item_total

                # Remove products whose demand
                # has been completely allocated

                remaining_products = [

                    item
                    for item in remaining_products
                    if item["quantity"] > 0
                ]

                order.total_amount = order_total

                # --------------------------------
                # Historical timestamp
                # --------------------------------

                historical_datetime = (
                    timezone.make_aware(
                        datetime.combine(
                            sale_date,
                            datetime.min.time()
                        )
                    )
                )

                order.created_at = (
                    historical_datetime
                    + timedelta(
                        hours=random.randint(
                            9,
                            21
                        ),
                        minutes=random.randint(
                            0,
                            59
                        )
                    )
                )

                order.save(
                    update_fields=[
                        "total_amount",
                        "created_at"
                    ]
                )

                total_orders += 1

                total_revenue += order_total

        # --------------------------------
        # Summary
        # --------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Historical sales data generated successfully!"
            )
        )

        self.stdout.write(
            f"Orders created: {total_orders}"
        )

        self.stdout.write(
            f"Total revenue: ₹{total_revenue:.2f}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Demo customer: demo_customer"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo password: demo123"
            )
        )