from django.contrib.auth.decorators import login_required
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
        return redirect("product_detail", product_id=product_id)

    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    if product.stock <= 0:
        return redirect("product_detail", product_id=product.id)

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if created:
        cart_item.quantity = 1

    elif cart_item.quantity < product.stock:
        cart_item.quantity += 1

    cart_item.save()

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

        elif quantity <= cart_item.product.stock:

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