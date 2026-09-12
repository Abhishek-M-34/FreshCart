from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from cart.models import Cart

from .forms import CategoryForm, ProductForm, StockBatchForm, StockBatchEditForm
from .models import Category, Product, StockBatch
from datetime import timedelta
from django.utils import timezone


def product_list(request):

    category_id = request.GET.get("category")

    products = Product.objects.filter(
        is_available=True
    )

    categories = Category.objects.all()

    if category_id:
        products = products.filter(
            category_id=category_id
        )
    available_products = []

    for product in products:
        if product.get_available_stock() > 0:
            available_products.append(product)
    cart_items = []
    cart_total_quantity = 0

    if request.user.is_authenticated:

        cart = Cart.objects.filter(
            user=request.user
        ).first()

        if cart:

            cart_items = cart.items.select_related(
                "product"
            ).order_by("id")

            cart_total_quantity = sum(
                item.quantity
                for item in cart_items
            )

    context = {
        "products": available_products,
        "categories": categories,
        "selected_category": category_id,
        "cart_items": cart_items,
        "cart_total_quantity": cart_total_quantity,
    }

    return render(
        request,
        "products/product_list.html",
        context
    )

def product_detail(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    if product.get_available_stock() <= 0:
        return redirect("product_list")

    return render(
        request,
        "products/product_detail.html",
        {"product": product}
    )

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
def admin_product_list(request):

    search_query = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()

    products = (
        Product.objects
        .select_related("category")
        .order_by("-id")
    )

    # Search
    if search_query:
        products = products.filter(
            name__icontains=search_query
        )

    # Category filter
    if category_id:
        products = products.filter(
            category_id=category_id
        )

    categories = Category.objects.all().order_by("name")

    # Group products category-wise
    category_sections = []

    for category in categories:

        category_products = products.filter(
            category=category
        )

        if category_products.exists():

            category_sections.append({
                "category": category,
                "products": category_products,
            })

    context = {
        "category_sections": category_sections,
        "categories": categories,
        "search_query": search_query,
        "selected_category": category_id,
    }

    return render(
        request,
        "dashboard/products/product_list.html",
        context
    )

@user_passes_test(is_admin)
def admin_product_add(request):

    if request.method == "POST":

        form = ProductForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_product_list"
            )

    else:

        form = ProductForm()

    return render(
        request,
        "dashboard/products/product_form.html",
        {
            "form": form,
            "title": "Add Product",
        }
    )

@user_passes_test(is_admin)
def admin_product_edit(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if request.method == "POST":

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_product_list"
            )

    else:

        form = ProductForm(
            instance=product
        )

    return render(
        request,
        "dashboard/products/product_form.html",
        {
            "form": form,
            "title": "Edit Product",
        }
    )

@user_passes_test(is_admin)
def admin_stock_add(request):

    if request.method == "POST":

        form = StockBatchForm(request.POST)

        if form.is_valid():

            stock_batch = form.save(commit=False)

            stock_batch.quantity_remaining = (
                stock_batch.quantity_received
            )

            if stock_batch.product.expiry_days > 0:
                stock_batch.expiry_date = (
                    stock_batch.arrival_date
                    + timedelta(
                        days=stock_batch.product.expiry_days
                    )
                )
            else:
                stock_batch.expiry_date = None

            stock_batch.save()

            return redirect(
                "admin_product_list"
            )

    else:
        form = StockBatchForm()

    return render(
        request,
        "dashboard/products/stock_form.html",
        {
            "form": form,
            "title": "Add Stock",
        }
    )

@user_passes_test(is_admin)
def admin_stock_discard(request, batch_id):

    stock_batch = get_object_or_404(
        StockBatch,
        id=batch_id
    )

    if request.method == "POST":
        stock_batch.quantity_remaining = 0
        stock_batch.save(update_fields=["quantity_remaining"])

    return redirect("admin_stock_list")

@user_passes_test(is_admin)
def admin_stock_list(request):

    stock_batches = (
        StockBatch.objects
        .select_related("product")
        .order_by(
            "expiry_date",
            "arrival_date",
            "id"
        )
    )

    today = timezone.localdate()

    product_summaries = []

    products = Product.objects.all().order_by("name")

    for product in products:

        product_batches = stock_batches.filter(
            product=product
        )

        total_received = 0
        available_quantity = 0
        expired_quantity = 0
        batch_count = 0

        batches = []

        for batch in product_batches:

            total_received += batch.quantity_received
            batch_count += 1

            if batch.quantity_remaining == 0:
                status = "Depleted"

            elif (
                batch.expiry_date is not None
                and batch.expiry_date < today
            ):
                expired_quantity += batch.quantity_remaining
                status = "Expired"

            else:
                available_quantity += batch.quantity_remaining
                status = "Active"

            batches.append({
                "batch": batch,
                "status": status,
            })

        if batch_count > 0:
            product_summaries.append({
                "product": product,
                "total_received": total_received,
                "available_quantity": available_quantity,
                "expired_quantity": expired_quantity,
                "batch_count": batch_count,
                "batches": batches,
            })

    return render(
        request,
        "dashboard/products/stock_list.html",
        {
            "product_summaries": product_summaries,
        }
    )

@user_passes_test(is_admin)
def admin_stock_edit(request, batch_id):

    stock_batch = get_object_or_404(
        StockBatch,
        id=batch_id
    )

    if request.method == "POST":

        form = StockBatchEditForm(
            request.POST,
            instance=stock_batch
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_stock_list"
            )

    else:

        form = StockBatchEditForm(
            instance=stock_batch
        )

    return render(
        request,
        "dashboard/products/stock_edit.html",
        {
            "form": form,
            "stock_batch": stock_batch,
            "title": "Edit Stock Batch",
        }
    )

@user_passes_test(is_admin)
def admin_product_delete(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if request.method == "POST":

        product.delete()

    return redirect(
        "admin_product_list"
    )

@user_passes_test(is_admin)
def admin_category_list(request):

    categories = Category.objects.all().order_by("name")

    return render(
        request,
        "dashboard/categories/category_list.html",
        {
            "categories": categories
        }
    )

@user_passes_test(is_admin)
def admin_category_add(request):

    if request.method == "POST":

        form = CategoryForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect(
                "admin_category_list"
            )

    else:

        form = CategoryForm()

    return render(
        request,
        "dashboard/categories/category_form.html",
        {
            "form": form,
            "title": "Add Category",
        }
    )

@user_passes_test(is_admin)
def admin_category_edit(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id
    )

    if request.method == "POST":

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_category_list"
            )

    else:

        form = CategoryForm(
            instance=category
        )

    return render(
        request,
        "dashboard/categories/category_form.html",
        {
            "form": form,
            "title": "Edit Category",
        }
    )

@user_passes_test(is_admin)
def admin_category_delete(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id
    )

    if request.method == "POST":

        category.delete()

    return redirect(
        "admin_category_list"
    )

