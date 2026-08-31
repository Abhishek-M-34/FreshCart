from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth.decorators import user_passes_test

from .forms import OrderStatusForm
from .models import Order

from cart.models import Cart
from products.models import Product

from .forms import CheckoutForm
from .models import Order, OrderItem


@login_required
def checkout(request):

    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    items = cart.items.select_related("product")

    for item in items:
        item.subtotal = item.product.price * item.quantity
    if not items.exists():
        return redirect("cart")

    total = sum(
    item.subtotal
    for item in items
)

    if request.method == "POST":

        form = CheckoutForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                # Check stock before creating the order
                for item in items:

                    product = Product.objects.select_for_update().get(
                        id=item.product.id
                    )

                    if (
                        not product.is_available
                        or product.stock < item.quantity
                    ):
                        return render(
                            request,
                            "orders/checkout.html",
                            {
                                "form": form,
                                "items": items,
                                "total": total,
                                "error": (
                                    f"{product.name} is no longer "
                                    "available in the requested quantity."
                                ),
                            }
                        )

                # Create order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=total,
                    shipping_address=form.cleaned_data[
                        "shipping_address"
                    ],
                    status="pending",
                )

                # Create order items and reduce stock
                for item in items:

                    product = Product.objects.select_for_update().get(
                        id=item.product.id
                    )

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        price=product.price,
                        quantity=item.quantity,
                    )

                    product.stock -= item.quantity

                    if product.stock == 0:
                        product.is_available = False

                    product.save()

                # Clear cart
                cart.items.all().delete()

            return redirect(
                "order_success",
                order_id=order.id
            )

    else:
        form = CheckoutForm()

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "items": items,
            "total": total,
        }
    )


@login_required
def order_success(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
        request,
        "orders/order_success.html",
        {"order": order}
    )

@login_required
def order_history(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "orders/order_history.html",
        {"orders": orders}
    )

@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    items = order.items.all()

    for item in items:
        item.subtotal = item.price * item.quantity

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "items": items,
        }
    )

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
def admin_order_list(request):

    orders = (
        Order.objects
        .select_related("user")
        .order_by("-created_at")
    )

    return render(
        request,
        "dashboard/orders/order_list.html",
        {
            "orders": orders
        }
    )

@user_passes_test(is_admin)
def admin_order_detail(request, order_id):

    order = get_object_or_404(
        Order.objects.select_related("user"),
        id=order_id
    )

    items = order.items.select_related("product")

    for item in items:
        item.subtotal = item.price * item.quantity

    return render(
        request,
        "dashboard/orders/order_detail.html",
        {
            "order": order,
            "items": items,
        }
    )

@user_passes_test(is_admin)
def admin_order_update(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    if request.method == "POST":

        form = OrderStatusForm(
            request.POST,
            instance=order
        )

        if form.is_valid():

            form.save()

            return redirect(
                "admin_order_detail",
                order_id=order.id
            )

    else:

        form = OrderStatusForm(
            instance=order
        )

    return render(
        request,
        "dashboard/orders/order_update.html",
        {
            "order": order,
            "form": form,
        }
    )

