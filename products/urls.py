from django.urls import path

from . import views


urlpatterns = [

    # Customer

    path(
        "products/",
        views.product_list,
        name="product_list"
    ),

    path(
        "products/<int:product_id>/",
        views.product_detail,
        name="product_detail"
    ),


    # Admin Products

    path(
        "admin-dashboard/products/",
        views.admin_product_list,
        name="admin_product_list"
    ),

    path(
        "admin-dashboard/products/add/",
        views.admin_product_add,
        name="admin_product_add"
    ),

    path(
        "admin-dashboard/products/<int:product_id>/edit/",
        views.admin_product_edit,
        name="admin_product_edit"
    ),

    path(
        "admin-dashboard/products/<int:product_id>/delete/",
        views.admin_product_delete,
        name="admin_product_delete"
    ),


    # Admin Categories

    path(
        "admin-dashboard/categories/",
        views.admin_category_list,
        name="admin_category_list"
    ),

    path(
        "admin-dashboard/categories/add/",
        views.admin_category_add,
        name="admin_category_add"
    ),

    path(
        "admin-dashboard/categories/<int:category_id>/edit/",
        views.admin_category_edit,
        name="admin_category_edit"
    ),

    path(
        "admin-dashboard/categories/<int:category_id>/delete/",
        views.admin_category_delete,
        name="admin_category_delete"
    ),
    path(
        "admin-dashboard/products/stock/add/",
        views.admin_stock_add,
        name="admin_stock_add"
    ),
    path(
        "admin-dashboard/products/stock/",
        views.admin_stock_list,
        name="admin_stock_list"
    ),
    path(
        "admin-dashboard/products/stock/<int:batch_id>/edit/",
        views.admin_stock_edit,
        name="admin_stock_edit"
    ),
    path(
        "admin-dashboard/products/stock/<int:batch_id>/discard/",
        views.admin_stock_discard,
        name="admin_stock_discard"
    ),
]