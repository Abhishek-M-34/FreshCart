from decimal import Decimal
import uuid

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth.decorators import user_passes_test

from .forms import OrderStatusForm
from .models import DemoPaymentSession, Order

from cart.models import Cart
from products.models import Product, StockBatch

from .forms import CheckoutForm
from .models import Order, OrderItem

from django.utils import timezone
from django.db.models import F


class CheckoutInventoryError(Exception):
    pass


class CheckoutCartError(Exception):
    pass


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


def _format_shipping_address(data):
    if data.get("shipping_address"):
        return data["shipping_address"]

    return ", ".join(
        part
        for part in [
            data.get("building"),
            data.get("street"),
            data.get("city"),
            data.get("district"),
            data.get("state"),
            data.get("pin_code"),
        ]
        if part
    )


def _create_order_from_checkout_data(
    user,
    data,
    payment_status="PENDING",
    transaction_id="",
):
    with transaction.atomic():
        cart = (
            Cart.objects
            .select_for_update()
            .filter(user=user)
            .first()
        )

        if cart is None:
            raise CheckoutCartError

        items = list(
            cart.items
            .select_related("product")
            .all()
        )

        if not items:
            raise CheckoutCartError

        today = timezone.localdate()
        order_item_prices = []

        for item in items:
            product = Product.objects.select_for_update().get(
                id=item.product.id
            )

            if not product.is_available:
                raise CheckoutInventoryError(
                    f"{product.name} is no longer available."
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

            valid_batches = [
                batch
                for batch in batches
                if batch.expiry_date is None
                or batch.expiry_date >= today
            ]

            available_quantity = sum(
                batch.quantity_remaining
                for batch in valid_batches
            )

            if available_quantity < item.quantity:
                raise CheckoutInventoryError(
                    f"{product.name} is no longer available in the requested quantity."
                )

            line_total, effective_unit_price = (
                get_effective_pricing_for_quantity(
                    product,
                    item.quantity,
                )
            )
            order_item_prices.append({
                "item": item,
                "product": product,
                "unit_price": effective_unit_price,
            })

        order_total = sum(
            get_effective_pricing_for_quantity(
                item_data["product"],
                item_data["item"].quantity,
            )[0]
            for item_data in order_item_prices
        )

        checkout_key = data.get("checkout_key") or str(uuid.uuid4())
        existing_order = Order.objects.filter(
            user=user,
            checkout_key=checkout_key,
        ).first()

        if existing_order:
            return existing_order

        order = Order.objects.create(
            user=user,
            total_amount=order_total,
            shipping_address=_format_shipping_address(data),
            recipient_name=data.get("recipient_name", ""),
            building=data.get("building", ""),
            street=data.get("street", ""),
            city=data.get("city", ""),
            district=data.get("district", ""),
            state=data.get("state", "Kerala"),
            pin_code=data.get("pin_code", ""),
            phone=data.get("phone", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            payment_method=data.get("payment_method", "COD"),
            payment_status=payment_status,
            transaction_id=transaction_id,
            checkout_key=checkout_key,
            status="pending",
        )

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
                if batch.expiry_date is not None and batch.expiry_date < today:
                    continue

                if remaining_to_consume <= 0:
                    break

                quantity_from_batch = min(
                    batch.quantity_remaining,
                    remaining_to_consume
                )
                batch.quantity_remaining -= quantity_from_batch
                batch.save(update_fields=["quantity_remaining"])
                remaining_to_consume -= quantity_from_batch

        cart.items.all().delete()

        return order

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("product")

    for item in items:
        pricing = get_effective_pricing_details(item.product, item.quantity)
        item.effective_unit_price = pricing["effective_unit_price"]
        item.discount_percentage = pricing["discount_percentage"]
        item.subtotal = pricing["effective_unit_price"] * item.quantity

    if not items.exists():
        return redirect("cart")

    total = sum(item.subtotal for item in items)

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            checkout_key = data.get("checkout_key") or str(uuid.uuid4())
            data["checkout_key"] = checkout_key

            if data.get("payment_method") == "ONLINE":
                payment_session, created = DemoPaymentSession.objects.get_or_create(
                    checkout_key=checkout_key,
                    defaults={
                        "user": request.user,
                        "payload": {
                            key: str(value) if value is not None else ""
                            for key, value in data.items()
                        },
                        "amount": total,
                    },
                )
                if payment_session.user_id != request.user.id:
                    return render(
                        request,
                        "orders/checkout.html",
                        {"form": form, "items": items, "total": total, "error": "Payment session is invalid."},
                    )
                return redirect("demo_payment", session_key=payment_session.session_key)

            try:
                order = _create_order_from_checkout_data(request.user, data)
            except CheckoutInventoryError as error:
                return render(
                    request,
                    "orders/checkout.html",
                    {"form": form, "items": items, "total": total, "error": str(error)},
                )
            except CheckoutCartError:
                return redirect("cart")

            return redirect("order_success", order_id=order.id)
    else:
        form = CheckoutForm(initial={
            "checkout_key": str(uuid.uuid4()),
            "state": "Kerala",
        })

    return render(
        request,
        "orders/checkout.html",
        {"form": form, "items": items, "total": total},
    )


def _complete_demo_payment(payment_session):
    with transaction.atomic():
        payment_session = (
            DemoPaymentSession.objects
            .select_for_update()
            .select_related("user")
            .get(id=payment_session.id)
        )

        if payment_session.status == "success" and payment_session.order_id:
            return payment_session.order

        transaction_id = (
            f"FC-DEMO-{uuid.uuid4().hex[:10].upper()}"
        )
        order = _create_order_from_checkout_data(
            payment_session.user,
            payment_session.payload,
            payment_status="PAID_DEMO",
            transaction_id=transaction_id,
        )
        payment_session.status = "success"
        payment_session.transaction_id = transaction_id
        payment_session.order = order
        payment_session.save(
            update_fields=["status", "transaction_id", "order"]
        )

        return order


@login_required
def demo_payment(request, session_key):
    payment_session = get_object_or_404(
        DemoPaymentSession,
        session_key=session_key,
        user=request.user,
    )

    if request.method == "POST":
        try:
            order = _complete_demo_payment(payment_session)
        except CheckoutInventoryError as error:
            return render(
                request,
                "orders/payment_demo.html",
                {
                    "payment_session": payment_session,
                    "error": str(error),
                },
            )
        except CheckoutCartError:
            return redirect("cart")

        return redirect("order_success", order_id=order.id)

    return render(
        request,
        "orders/payment_demo.html",
        {
            "payment_session": payment_session,
            "qr_payload": (
                f"FRESHCART-DEMO-PAYMENT:{payment_session.session_key}"
            ),
        },
    )


def demo_payment_confirm(request, session_key):
    payment_session = get_object_or_404(
        DemoPaymentSession,
        session_key=session_key,
    )

    if payment_session.status != "success":
        try:
            _complete_demo_payment(payment_session)
        except (CheckoutInventoryError, CheckoutCartError) as error:
            return render(
                request,
                "orders/payment_confirmed.html",
                {"error": str(error)},
                status=409,
            )

    return render(
        request,
        "orders/payment_confirmed.html",
        {"payment_session": payment_session},
    )


def demo_payment_status(request, session_key):
    payment_session = get_object_or_404(
        DemoPaymentSession,
        session_key=session_key,
    )

    return JsonResponse({
        "status": payment_session.status,
        "transaction_id": payment_session.transaction_id,
        "order_id": payment_session.order_id,
    })

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

