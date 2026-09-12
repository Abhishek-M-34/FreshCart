from django import forms

from .models import Category, Product, StockBatch


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
    "name",
    "category",
    "description",
    "price",
    "stock",
    "expiry_days",
    "image",
    "is_available",
]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01"
                }
            ),

            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0"
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "is_available": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),
            "expiry_days": forms.NumberInput(
    attrs={
        "class": "form-control",
        "min": "0"
    }
),
        }

class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category

        fields = [
            "name",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Category name"
                }
            ),
        }

class StockBatchForm(forms.ModelForm):

    class Meta:
        model = StockBatch
        fields = [
            "product",
            "quantity_received",
            "arrival_date",
        ]

        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
            "quantity_received": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1"
                }
            ),
            "arrival_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),
        }

class StockBatchEditForm(forms.ModelForm):

    class Meta:
        model = StockBatch
        fields = [
            "quantity_remaining",
            "arrival_date",
            "expiry_date",
        ]

        widgets = {
            "quantity_remaining": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0"
                }
            ),
            "arrival_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),
            "expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),
        }

    def clean_quantity_remaining(self):
        quantity_remaining = self.cleaned_data["quantity_remaining"]

        if quantity_remaining > self.instance.quantity_received:
            raise forms.ValidationError(
                "Remaining quantity cannot be greater than received quantity."
            )

        return quantity_remaining