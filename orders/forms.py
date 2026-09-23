from django import forms
from django.core.validators import RegexValidator
from .models import Order


class CheckoutForm(forms.Form):
    recipient_name = forms.CharField(
        required=False,
        max_length=200,
        label="Full name",
    )
    building = forms.CharField(
        required=False,
        max_length=200,
        label="Building / House number",
    )
    street = forms.CharField(
        required=False,
        max_length=200,
        label="Street / Area",
    )
    city = forms.CharField(required=False, max_length=100, label="City")
    district = forms.CharField(required=False, max_length=100, label="District")
    state = forms.CharField(required=False, max_length=100, initial="Kerala")
    pin_code = forms.CharField(
        required=False,
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "Enter a valid 6-digit PIN code.")],
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        validators=[RegexValidator(r"^[0-9+()\-\s]{7,20}$", "Enter a valid phone number.")],
    )
    latitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        required=False,
        initial="COD",
        widget=forms.RadioSelect,
    )
    checkout_key = forms.CharField(required=False, widget=forms.HiddenInput)
    shipping_address = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Enter your complete delivery address"
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()
        legacy_address = cleaned_data.get("shipping_address", "").strip()
        structured_fields = [
            "recipient_name",
            "building",
            "street",
            "city",
            "district",
            "state",
            "pin_code",
            "phone",
        ]

        if legacy_address and not any(cleaned_data.get(field) for field in structured_fields):
            cleaned_data["payment_method"] = cleaned_data.get("payment_method") or "COD"
            return cleaned_data

        cleaned_data["payment_method"] = cleaned_data.get("payment_method") or "COD"

        for field in structured_fields:
            if not cleaned_data.get(field):
                self.add_error(field, "This field is required.")

        if cleaned_data.get("latitude") is None or cleaned_data.get("longitude") is None:
            raise forms.ValidationError("Select a delivery location on the map.")

        if not -90 <= cleaned_data["latitude"] <= 90:
            self.add_error("latitude", "Select a valid latitude.")

        if not -180 <= cleaned_data["longitude"] <= 180:
            self.add_error("longitude", "Select a valid longitude.")

        if not cleaned_data.get("checkout_key"):
            self.add_error("checkout_key", "Checkout session is missing.")

        return cleaned_data

class OrderStatusForm(forms.ModelForm):

    class Meta:
        model = Order

        fields = [
            "status",
        ]

        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
        }