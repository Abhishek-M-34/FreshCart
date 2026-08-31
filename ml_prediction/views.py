import pandas as pd
import plotly.graph_objects as go

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from sklearn.ensemble import RandomForestRegressor

from orders.models import OrderItem
from products.models import Product


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
                    "date": future_date,
                    "predicted_quantity": round(
                        predicted_quantity
                    )
                }
            )

    return all_predictions


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

    chart = go.Figure()

    for product in (
        prediction_df["product"].unique()
    ):

        product_predictions = (
            prediction_df[
                prediction_df["product"] == product
            ]
        )

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

    chart.update_layout(
        title="7-Day Product Demand Forecast",
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

        predicted_demand = demand.get(
            product.name,
            0
        )

        current_stock = product.stock

        stock_after_forecast = (
            current_stock
            - predicted_demand
        )

        recommended_reorder = max(
            0,
            predicted_demand
            - current_stock
        )

        if current_stock <= 0:

            status = "Out of Stock"

        elif stock_after_forecast < 0:

            status = "Reorder Required"

        elif stock_after_forecast <= (
            predicted_demand * 0.25
        ):

            status = "Low Stock"

        else:

            status = "Stock Sufficient"

        inventory_data.append(
            {
                "product": product.name,

                "current_stock": current_stock,

                "predicted_demand": round(
                    predicted_demand
                ),

                "stock_after_forecast": round(
                    stock_after_forecast
                ),

                "recommended_reorder": round(
                    recommended_reorder
                ),

                "status": status,
            }
        )

    return render(
        request,
        "dashboard/inventory_prediction.html",
        {
            "inventory_data": inventory_data,
        }
    )