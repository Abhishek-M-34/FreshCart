from django import forms

from .models import Category, Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "name",
            "category",
            "description",
            "price",
            "stock",
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