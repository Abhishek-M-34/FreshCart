from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from products.models import Product

from .models import Cart, CartItem


@login_required
def cart_view(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    items = cart.items.select_related("product")

    for item in items:
        item.subtotal = item.product.price * item.quantity

    total = sum(
        item.subtotal
        for item in items
    )

    return render(
        request,
        "cart/cart.html",
        {
            "cart": cart,
            "items": items,
            "total": total,
        }
    )


@login_required
def add_to_cart(request, product_id):

    if request.method != "POST":
        return redirect(
            "product_detail",
            product_id=product_id
        )

    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    available_stock = product.get_available_stock()

    if available_stock <= 0:

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "message": "This product is out of stock."
                },
                status=400
            )

        return redirect(
            "product_detail",
            product_id=product.id
        )

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if created:
        cart_item.quantity = 1

    elif cart_item.quantity < available_stock:
        cart_item.quantity += 1

    cart_item.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        cart_items = cart.items.select_related(
            "product"
        ).order_by("id")

        cart_total_quantity = sum(
            item.quantity
            for item in cart_items
        )

        items = [
            {
                "name": item.product.name,
                "quantity": item.quantity,
            }
            for item in cart_items
        ]

        return JsonResponse(
    {
        "success": True,
        "cart_total_quantity": cart_total_quantity,
        "added_product_name": product.name,
        "items": items,
    }
)

    return redirect("cart")

@login_required
def update_cart(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    if request.method == "POST":

        try:
            quantity = int(
                request.POST.get("quantity", 1)
            )
        except (TypeError, ValueError):
            quantity = 1

        if quantity <= 0:

            cart_item.delete()

        elif quantity <= cart_item.product.get_available_stock():
            cart_item.quantity = quantity
            cart_item.save()

    return redirect("cart")


@login_required
def remove_from_cart(request, item_id):

    if request.method != "POST":
        return redirect("cart")

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.delete()

    return redirect("cart")