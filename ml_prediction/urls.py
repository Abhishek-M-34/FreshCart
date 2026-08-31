from django.urls import path

from . import views


urlpatterns = [

    path(
        "sales-prediction/",
        views.sales_prediction,
        name="sales_prediction"
    ),

    path(
        "inventory-prediction/",
        views.inventory_prediction,
        name="inventory_prediction"
    ),

]