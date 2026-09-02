from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm, ProductForm

from .models import Category, Product


def product_list(request):

    category_id = request.GET.get("category")

    products = Product.objects.filter(
        is_available=True,
        stock__gt=0
    )

    categories = Category.objects.all()

    if category_id:
        products = products.filter(
            category_id=category_id
        )

    context = {
        "products": products,
        "categories": categories,
        "selected_category": category_id,
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

    if search_query:
        products = products.filter(
            name__icontains=search_query
        )

    if category_id:
        products = products.filter(
            category_id=category_id
        )

    categories = Category.objects.all().order_by("name")

    return render(
        request,
        "dashboard/products/product_list.html",
        {
            "products": products,
            "categories": categories,
            "search_query": search_query,
            "selected_category": category_id,
        }
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

