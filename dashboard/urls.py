from django.urls import path

from . import views


urlpatterns = [
    path(
        "admin-dashboard/",
        views.dashboard,
        name="admin_dashboard"
    ),
    path(
    "admin-dashboard/customers/",
    views.admin_customer_list,
    name="admin_customer_list"
),

path(
    "admin-dashboard/customers/<int:customer_id>/",
    views.admin_customer_detail,
    name="admin_customer_detail"
),
path(
    "admin-dashboard/analytics/",
    views.analytics,
    name="analytics"
),
]