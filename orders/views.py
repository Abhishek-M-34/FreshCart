from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth.decorators import user_passes_test

from .forms import OrderStatusForm
from .models import Order

from cart.models import Cart
from products.models import Product, StockBatch

from .forms import CheckoutForm
from .models import Order, OrderItem

from django.utils import timezone
from django.db.models import F


def get_effective_pricing_details(product, quantity):
    if quantity <= 0:
        return {
            "subtotal": Decimal("0"),
            "effective_unit_price": Decimal("0"),
            "discount_percentage": 0,
        }

    today = timezone.localdate()

    valid_batches = []

    for batch in (
        StockBatch.objects
        .filter(
            product=product,
            quantity_remaining__gt=0,
        )
        .order_by(
            F("expiry_date").asc(nulls_last=True),
            "arrival_date",
            "id",
        )
    ):
        if batch.expiry_date is None:
            valid_batches.append(batch)
        elif batch.expiry_date >= today:
            valid_batches.append(batch)

    remaining_quantity = quantity
    subtotal = Decimal("0")
    pricing_segments = []

    for batch in valid_batches:
        if remaining_quantity <= 0:
            break

        quantity_from_batch = min(
            batch.quantity_remaining,
            remaining_quantity,
        )

        discount_percentage = batch.get_discount_percentage(
            expected_demand=0
        )

        unit_price = (
            batch.get_discounted_price(expected_demand=0)
            if discount_percentage > 0
            else product.price
        )

        subtotal += (
            Decimal(quantity_from_batch) * unit_price
        )
        pricing_segments.append(
            (quantity_from_batch, discount_percentage)
        )
        remaining_quantity -= quantity_from_batch

    if remaining_quantity > 0:
        subtotal += Decimal(remaining_quantity) * product.price
        pricing_segments.append((remaining_quantity, 0))

    effective_unit_price = (
        subtotal / Decimal(quantity)
        if quantity > 0 else Decimal("0")
    )

    discounts = {
        discount_percentage
        for segment_quantity, discount_percentage in pricing_segments
        if segment_quantity > 0
    }

    return {
        "subtotal": subtotal,
        "effective_unit_price": effective_unit_price,
        "discount_percentage": (
            discounts.pop()
            if len(discounts) == 1
            else 0
        ),
    }


def get_effective_pricing_for_quantity(product, quantity):
    pricing = get_effective_pricing_details(product, quantity)
    return pricing["subtotal"], pricing["effective_unit_price"]

@login_required
def checkout(request):
    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    items = cart.items.select_related("product")

    for item in items:
        pricing = get_effective_pricing_details(
            item.product,
            item.quantity,
        )
        item.effective_unit_price = pricing["effective_unit_price"]
        item.discount_percentage = pricing["discount_percentage"]
        item.subtotal = pricing["effective_unit_price"]
        item.subtotal *= item.quantity

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

                today = timezone.localdate()

                # Check stock for every cart item
                for item in items:

                    product = Product.objects.select_for_update().get(
                        id=item.product.id
                    )

                    if not product.is_available:
                        return render(
                            request,
                            "orders/checkout.html",
                            {
                                "form": form,
                                "items": items,
                                "total": total,
                                "error": (
                                    f"{product.name} is no longer "
                                    "available."
                                ),
                            }
                        )

                    batches = (
                        StockBatch.objects
                        .select_for_update()
                        .filter(
                            product=product,
                            quantity_remaining__gt=0
                        )
                        .order_by(
    F("expiry_date").asc(nulls_last=True),
    "arrival_date",
    "id"
)
                    )

                    valid_batches = []

                    for batch in batches:

                        if batch.expiry_date is None:
                            valid_batches.append(batch)

                        elif batch.expiry_date >= today:
                            valid_batches.append(batch)

                    available_quantity = sum(
                        batch.quantity_remaining
                        for batch in valid_batches
                    )

                    if available_quantity < item.quantity:
                        return render(
                            request,
                            "orders/checkout.html",
                            {
                                "form": form,
                                "items": items,
                                "total": total,
                                "error": (
                                    f"{product.name} is no longer "
                                    "available in the requested "
                                    "quantity."
                                ),
                            }
                        )

                order_total = Decimal("0")
                order_item_prices = []

                for item in items:
                    product = Product.objects.select_for_update().get(
                        id=item.product.id
                    )

                    line_total, effective_unit_price = (
                        get_effective_pricing_for_quantity(
                            product,
                            item.quantity,
                        )
                    )
                    order_total += line_total
                    order_item_prices.append({
                        "item": item,
                        "product": product,
                        "unit_price": effective_unit_price,
                    })

                # Create order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=order_total,
                    shipping_address=form.cleaned_data[
                        "shipping_address"
                    ],
                    status="pending",
                )

                # Create order items and consume stock using FEFO
                for item_data in order_item_prices:

                    product = item_data["product"]
                    item = item_data["item"]

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        price=item_data["unit_price"],
                        quantity=item.quantity,
                    )

                    remaining_to_consume = item.quantity

                    batches = (
                        StockBatch.objects
                        .select_for_update()
                        .filter(
                            product=product,
                            quantity_remaining__gt=0
                        )
                        .order_by(
    F("expiry_date").asc(nulls_last=True),
    "arrival_date",
    "id"
)
                    )

                    for batch in batches:

                        if batch.expiry_date is not None:
                            if batch.expiry_date < today:
                                continue

                        if remaining_to_consume <= 0:
                            break

                        quantity_from_batch = min(
                            batch.quantity_remaining,
                            remaining_to_consume
                        )

                        batch.quantity_remaining -= (
                            quantity_from_batch
                        )

                        batch.save(
                            update_fields=[
                                "quantity_remaining"
                            ]
                        )

                        remaining_to_consume -= (
                            quantity_from_batch
                        )

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

    search_query = request.GET.get("search", "").strip()
    selected_date = request.GET.get("date", "").strip()
    selected_status = request.GET.get("status", "").strip()

    if search_query:
        from django.db.models import Q

        orders = orders.filter(
            Q(id__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

    if selected_date:
        orders = orders.filter(
            created_at__date=selected_date
        )

    if selected_status:
        orders = orders.filter(
            status=selected_status
        )

    return render(
        request,
        "dashboard/orders/order_list.html",
        {
            "orders": orders,
            "search_query": search_query,
            "selected_date": selected_date,
            "selected_status": selected_status,
            "status_choices": Order.STATUS_CHOICES,
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

