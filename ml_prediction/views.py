import pandas as pd
import plotly.graph_objects as go

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from sklearn.ensemble import RandomForestRegressor

from orders.models import OrderItem
from products.models import Product

from django.utils import timezone
from datetime import timedelta


def is_admin(user):
    return user.is_authenticated and user.is_staff


def generate_predictions():

    sales = (
        OrderItem.objects
        .filter(order__status="delivered")
        .annotate(
            day=TruncDate("order__created_at")
        )
        .values(
            "product_name",
            "day"
        )
        .annotate(
            quantity_sold=Sum("quantity")
        )
        .order_by(
            "product_name",
            "day"
        )
    )

    data = list(sales)

    if not data:
        return []

    df = pd.DataFrame(data)

    df["day"] = pd.to_datetime(df["day"])

    df["quantity_sold"] = (
        df["quantity_sold"]
        .astype(float)
    )

    all_products = df["product_name"].unique()

    all_dates = pd.date_range(
        start=df["day"].min(),
        end=df["day"].max(),
        freq="D"
    )

    complete_index = pd.MultiIndex.from_product(
        [
            all_products,
            all_dates
        ],
        names=[
            "product_name",
            "day"
        ]
    )

    df = (
        df.set_index(
            [
                "product_name",
                "day"
            ]
        )
        .reindex(
            complete_index,
            fill_value=0
        )
        .reset_index()
    )

    all_predictions = []

    product_categories = {
        product.name: product.category.name
        for product in Product.objects.select_related("category")
    }

    for product_name in all_products:

        product_df = df[
            df["product_name"] == product_name
        ].copy()

        product_df = product_df.sort_values(
            "day"
        )

        product_df["day_number"] = (
            product_df["day"]
            - df["day"].min()
        ).dt.days

        product_df["day_of_week"] = (
            product_df["day"]
            .dt.dayofweek
        )

        product_df["month"] = (
            product_df["day"]
            .dt.month
        )

        product_df["is_weekend"] = (
            product_df["day_of_week"] >= 5
        ).astype(int)

        product_df["lag_1"] = (
            product_df["quantity_sold"]
            .shift(1)
        )

        product_df["lag_7"] = (
            product_df["quantity_sold"]
            .shift(7)
        )

        product_df["rolling_7"] = (
            product_df["quantity_sold"]
            .shift(1)
            .rolling(7)
            .mean()
        )

        product_df = product_df.dropna()

        if len(product_df) < 10:
            continue

        features = [
            "day_number",
            "day_of_week",
            "month",
            "is_weekend",
            "lag_1",
            "lag_7",
            "rolling_7",
        ]

        X = product_df[features]

        y = product_df["quantity_sold"]

        model = RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            max_depth=8
        )

        model.fit(X, y)

        last_date = product_df["day"].max()

        last_day_number = (
            product_df["day_number"].max()
        )

        last_lag_1 = (
            product_df["quantity_sold"].iloc[-1]
        )

        last_lag_7 = (
            product_df["quantity_sold"].iloc[-7]
        )

        last_rolling_7 = (
            product_df["quantity_sold"]
            .tail(7)
            .mean()
        )

        for i in range(1, 8):

            future_date = (
                last_date
                + pd.Timedelta(days=i)
            )

            future_day_number = (
                last_day_number + i
            )

            future_day_of_week = (
                future_date.dayofweek
            )

            future_month = (
                future_date.month
            )

            future_weekend = int(
                future_day_of_week >= 5
            )

            future_features = pd.DataFrame(
                [
                    {
                        "day_number": future_day_number,
                        "day_of_week": future_day_of_week,
                        "month": future_month,
                        "is_weekend": future_weekend,
                        "lag_1": last_lag_1,
                        "lag_7": last_lag_7,
                        "rolling_7": last_rolling_7,
                    }
                ]
            )

            predicted_quantity = model.predict(
                future_features
            )[0]

            predicted_quantity = max(
                predicted_quantity,
                0
            )

            all_predictions.append(
                {
                    "product": product_name,
                    "category": product_categories.get(
                        product_name,
                        "Uncategorized"
                    ),
                    "date": future_date,
                    "predicted_quantity": round(
                        predicted_quantity
                    )
                }
            )

    return all_predictions


def get_product_demand_prediction(product, horizon_days=None):
    """Return the existing forecast total for one product and horizon."""
    default_horizon = 7
    horizon = product.expiry_days or default_horizon

    if horizon_days is not None:
        horizon = horizon_days or default_horizon

    predictions = [
        prediction
        for prediction in generate_predictions()
        if prediction["product"] == product.name
    ]

    if not predictions:
        return None

    available_days = min(horizon, len(predictions))
    predicted_demand = sum(
        prediction["predicted_quantity"]
        for prediction in predictions[:available_days]
    )

    if horizon > len(predictions):
        predicted_demand *= horizon / len(predictions)

    return round(predicted_demand)


@user_passes_test(is_admin)
def sales_prediction(request):

    predictions = generate_predictions()

    if not predictions:

        return render(
            request,
            "dashboard/sales_prediction.html",
            {
                "error": (
                    "Not enough historical data "
                    "for product prediction."
                )
            }
        )

    prediction_df = pd.DataFrame(
        predictions
    )

    selected_category = request.GET.get(
        "category",
        ""
    )

    categories = sorted(
        prediction_df["category"]
        .dropna()
        .unique()
        .tolist()
    )

    chart = go.Figure()

    if selected_category:
        chart_data = prediction_df[
            prediction_df["category"] == selected_category
        ]

        for product in chart_data["product"].unique():

            product_predictions = chart_data[
                chart_data["product"] == product
            ]

            chart.add_trace(
                go.Scatter(
                    x=product_predictions["date"],
                    y=product_predictions[
                        "predicted_quantity"
                    ],
                    mode="lines+markers",
                    name=product
                )
            )

        chart_title = (
            f"7-Day {selected_category} "
            "Product Demand Forecast"
        )

    else:
        category_data = (
            prediction_df
            .groupby(
                ["category", "date"],
                as_index=False
            )["predicted_quantity"]
            .sum()
        )

        for category in category_data["category"].unique():

            category_predictions = category_data[
                category_data["category"] == category
            ]

            chart.add_trace(
                go.Scatter(
                    x=category_predictions["date"],
                    y=category_predictions[
                        "predicted_quantity"
                    ],
                    mode="lines+markers",
                    name=category
                )
            )

        chart_title = (
            "7-Day Category Demand Forecast"
        )

    chart.update_layout(
        title=chart_title,
        xaxis_title="Date",
        yaxis_title="Predicted Units",
        template="plotly_white"
    )

    chart_html = chart.to_html(
        full_html=False
    )

    return render(
        request,
        "dashboard/sales_prediction.html",
        {
            "predictions": predictions,
            "chart": chart_html,
            "categories": categories,
            "selected_category": selected_category,
        }
    )


@user_passes_test(is_admin)
def inventory_prediction(request):

    predictions = generate_predictions()

    if not predictions:

        return render(
            request,
            "dashboard/inventory_prediction.html",
            {
                "error": (
                    "Not enough historical data "
                    "for inventory prediction."
                )
            }
        )

    # -----------------------------------------
    # Calculate product-level demand
    # -----------------------------------------

    demand = {}

    for prediction in predictions:

        product_name = prediction["product"]

        quantity = prediction[
            "predicted_quantity"
        ]

        if product_name not in demand:
            demand[product_name] = 0

        demand[product_name] += quantity

    # -----------------------------------------
    # Get current stock
    # -----------------------------------------

    products = Product.objects.filter(
        name__in=demand.keys()
    )

    inventory_data = []

    for product in products:
        product_predictions = [
            prediction
            for prediction in predictions
            if prediction["product"] == product.name
        ]

        # Copy current usable batches into memory.
        # We do not modify the database during prediction.
        batches = []

        today = timezone.localdate()

        for batch in product.stock_batches.filter(
            quantity_remaining__gt=0
        ).order_by("expiry_date", "arrival_date", "id"):

            # Ignore already-expired batches.
            if batch.expiry_date is not None and batch.expiry_date < today:
                continue

            batches.append({
                "remaining": batch.quantity_remaining,
                "expiry_date": batch.expiry_date,
            })

        current_stock = sum(
            batch["remaining"]
            for batch in batches
        )

        predicted_demand = sum(
            prediction["predicted_quantity"]
            for prediction in product_predictions
        )

        projected_stock = current_stock

        stockout_date = None
        total_shortage = 0

        daily_projection = []

        # Track how much demand is expected to be
        # fulfilled from each batch before it expires.
        for prediction in product_predictions:

            daily_demand = prediction["predicted_quantity"]
            prediction_date = prediction["date"].date()

            # Remove batches that have already expired
            # by this prediction date.
            usable_batches = []

            for batch in batches:
                if (
                    batch["expiry_date"] is not None
                    and batch["expiry_date"] < prediction_date
                ):
                    continue

                usable_batches.append(batch)

            batches = usable_batches

            # Consume stock using FEFO.
            remaining_demand = daily_demand

            for batch in batches:

                if remaining_demand <= 0:
                    break

                consumed = min(
                    batch["remaining"],
                    remaining_demand
                )

                batch["remaining"] -= consumed
                remaining_demand -= consumed

            # Demand that could not be fulfilled from
            # currently available inventory.
            if remaining_demand > 0:
                total_shortage += remaining_demand

            projected_stock = sum(
                batch["remaining"]
                for batch in batches
            )

            if (
                projected_stock <= 0
                and stockout_date is None
            ):
                stockout_date = prediction_date

            daily_projection.append({
                "date": prediction_date,
                "demand": daily_demand,
                "remaining_stock": projected_stock,
            })

        stock_after_forecast = projected_stock

        safety_stock = round(predicted_demand * 0.20)

        reorder_date = None

        if stockout_date is not None:
            reorder_date = (
                stockout_date
                - timedelta(days=product.lead_time_days)
            )

        recommended_reorder = (
            total_shortage
            + max(0, safety_stock - stock_after_forecast)
        )

        reorder_required = (
            total_shortage > 0
            or stock_after_forecast < safety_stock
        )

        if current_stock <= 0:
            status = "Out of Stock"
        elif reorder_required:
            status = "Reorder Required"
        elif stock_after_forecast <= (
            predicted_demand * 0.25
        ):
            status = "Low Stock"
        else:
            status = "Stock Sufficient"

        discount_batches = []

        for batch in product.stock_batches.filter(
            quantity_remaining__gt=0
        ).order_by("expiry_date", "arrival_date", "id"):

            if batch.expiry_date is None:
                continue

            if batch.expiry_date < today:
                continue

            expected_demand_before_expiry = sum(
                projection["demand"]
                for projection in daily_projection
                if projection["date"] <= batch.expiry_date
            )

            discount_percentage = batch.get_discount_percentage(
                expected_demand=expected_demand_before_expiry
            )

            if discount_percentage > 0:
                discount_batches.append({
                    "batch_id": batch.id,
                    "expiry_date": batch.expiry_date,
                    "remaining_stock": batch.quantity_remaining,
                    "expected_demand_before_expiry": expected_demand_before_expiry,
                    "discount_percentage": discount_percentage,
                    "discounted_price": batch.get_discounted_price(
                        expected_demand=expected_demand_before_expiry
                    ),
                })

        inventory_data.append({
            "product": product.name,
            "current_stock": current_stock,
            "predicted_demand": round(predicted_demand),
            "stock_after_forecast": round(
                stock_after_forecast
            ),
            "recommended_reorder": round(
                recommended_reorder
            ),
            "stockout_date": stockout_date,
            "reorder_date": reorder_date,
            "daily_projection": daily_projection,
            "total_shortage": round(total_shortage),
            "safety_stock": safety_stock,
            "reorder_required": reorder_required,
            "status": status,
            "discount_batches": discount_batches,
        })

    return render(
        request,
        "dashboard/inventory_prediction.html",
        {
            "inventory_data": inventory_data,
            "discount_batches": discount_batches,
        }
    )