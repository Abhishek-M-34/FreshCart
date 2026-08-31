from django import forms
from .models import Order


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Enter your complete delivery address"
            }
        )
    )

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