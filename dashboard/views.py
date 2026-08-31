from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.shortcuts import render
from django.db.models import Count, Sum
from orders.models import Order, OrderItem
from products.models import Product
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
import json
import plotly.graph_objects as go


def is_admin(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin)
def dashboard(request):

    total_products = Product.objects.count()

    total_orders = Order.objects.count()

    total_customers = User.objects.filter(
        is_staff=False
    ).count()

    total_revenue = (
        Order.objects
        .filter(status="delivered")
        .aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    recent_orders = (
        Order.objects
        .select_related("user")
        .order_by("-created_at")[:5]
    )

    low_stock_products = (
        Product.objects
        .filter(stock__lte=10)
        .order_by("stock")[:5]
    )

    context = {
        "total_products": total_products,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "recent_orders": recent_orders,
        "low_stock_products": low_stock_products,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )

@user_passes_test(is_admin)
def admin_customer_list(request):

    customers = (
        User.objects
        .filter(is_staff=False)
        .annotate(
            order_count=Count("orders"),
            total_spent=Sum(
                "orders__total_amount",
                filter=models.Q(
                    orders__status="delivered"
                )
            )
        )
        .order_by("-date_joined")
    )

    return render(
        request,
        "dashboard/customers/customer_list.html",
        {
            "customers": customers
        }
    )

@user_passes_test(is_admin)
def admin_customer_detail(request, customer_id):

    customer = get_object_or_404(
        User,
        id=customer_id,
        is_staff=False
    )

    orders = (
        Order.objects
        .filter(user=customer)
        .order_by("-created_at")
    )

    total_spent = (
        orders
        .filter(status="delivered")
        .aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    return render(
        request,
        "dashboard/customers/customer_detail.html",
        {
            "customer": customer,
            "orders": orders,
            "total_spent": total_spent,
        }
    )

@user_passes_test(is_admin)
def analytics(request):

    delivered_orders = Order.objects.filter(
        status="delivered"
    )

    # -------------------------
    # Summary Statistics
    # -------------------------

    total_revenue = (
        delivered_orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0
    )

    total_orders = delivered_orders.count()

    average_order_value = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )


    # -------------------------
    # Daily Sales
    # -------------------------

    daily_sales = (
        delivered_orders
        .annotate(
            day=TruncDay("created_at")
        )
        .values("day")
        .annotate(
            revenue=Sum("total_amount")
        )
        .order_by("day")
    )


    # -------------------------
    # Monthly Sales
    # -------------------------

    monthly_sales = (
        delivered_orders
        .annotate(
            month=TruncMonth("created_at")
        )
        .values("month")
        .annotate(
            revenue=Sum("total_amount")
        )
        .order_by("month")
    )


    # -------------------------
    # Yearly Sales
    # -------------------------

    yearly_sales = (
        delivered_orders
        .annotate(
            year=TruncYear("created_at")
        )
        .values("year")
        .annotate(
            revenue=Sum("total_amount")
        )
        .order_by("year")
    )


    # -------------------------
    # Top Selling Products
    # -------------------------

    top_products = (
        OrderItem.objects
        .filter(
            order__status="delivered"
        )
        .values("product_name")
        .annotate(
            quantity_sold=Sum("quantity")
        )
        .order_by("-quantity_sold")[:10]
    )


    # -------------------------
    # Daily Chart
    # -------------------------

    daily_chart = go.Figure()

    daily_chart.add_trace(
        go.Scatter(
            x=[
                item["day"]
                for item in daily_sales
            ],
            y=[
                float(item["revenue"])
                for item in daily_sales
            ],
            mode="lines+markers",
            name="Daily Revenue"
        )
    )

    daily_chart.update_layout(
        title="Daily Sales",
        xaxis_title="Date",
        yaxis_title="Revenue (₹)",
        template="plotly_white"
    )


    # -------------------------
    # Monthly Chart
    # -------------------------

    monthly_chart = go.Figure()

    monthly_chart.add_trace(
        go.Bar(
            x=[
                item["month"]
                for item in monthly_sales
            ],
            y=[
                float(item["revenue"])
                for item in monthly_sales
            ],
            name="Monthly Revenue"
        )
    )

    monthly_chart.update_layout(
        title="Monthly Sales",
        xaxis_title="Month",
        yaxis_title="Revenue (₹)",
        template="plotly_white"
    )


    # -------------------------
    # Yearly Chart
    # -------------------------

    yearly_chart = go.Figure()

    yearly_chart.add_trace(
        go.Bar(
            x=[
                item["year"]
                for item in yearly_sales
            ],
            y=[
                float(item["revenue"])
                for item in yearly_sales
            ],
            name="Yearly Revenue"
        )
    )

    yearly_chart.update_layout(
        title="Yearly Sales",
        xaxis_title="Year",
        yaxis_title="Revenue (₹)",
        template="plotly_white"
    )


    # -------------------------
    # Product Chart
    # -------------------------

    product_chart = go.Figure()

    product_chart.add_trace(
        go.Bar(
            x=[
                item["quantity_sold"]
                for item in top_products
            ],
            y=[
                item["product_name"]
                for item in top_products
            ],
            orientation="h",
            name="Units Sold"
        )
    )

    product_chart.update_layout(
        title="Top Selling Products",
        xaxis_title="Units Sold",
        yaxis_title="Product",
        template="plotly_white"
    )


    context = {

        "total_revenue": total_revenue,

        "total_orders": total_orders,

        "average_order_value": average_order_value,

        "daily_chart": daily_chart.to_html(
            full_html=False
        ),

        "monthly_chart": monthly_chart.to_html(
            full_html=False
        ),

        "yearly_chart": yearly_chart.to_html(
            full_html=False
        ),

        "product_chart": product_chart.to_html(
            full_html=False
        ),
    }


    return render(
        request,
        "dashboard/analytics.html",
        context
    )