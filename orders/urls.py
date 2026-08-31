from django.urls import path

from . import views


urlpatterns = [
    path(
        "checkout/",
        views.checkout,
        name="checkout"
    ),

    path(
        "order/success/<int:order_id>/",
        views.order_success,
        name="order_success"
    ),

    path(
        "orders/",
        views.order_history,
        name="order_history"
    ),

    path(
        "orders/<int:order_id>/",
        views.order_detail,
        name="order_detail"
    ),
    path(
    "admin-dashboard/orders/",
    views.admin_order_list,
    name="admin_order_list"
),

path(
    "admin-dashboard/orders/<int:order_id>/",
    views.admin_order_detail,
    name="admin_order_detail"
),

path(
    "admin-dashboard/orders/<int:order_id>/update/",
    views.admin_order_update,
    name="admin_order_update"
),
]