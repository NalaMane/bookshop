from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "author", "description", "price", "stock", "erp_id", "cover_url"]
        help_texts = {
            "stock": "Number of copies. Books without stock can't be bought.",
            "erp_id": "Optional. The product ID in the ERP (the ISBN) – the next ERP import then updates this book.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stock"].required = True  # Lab 2 rule: no stock = can't be sold

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price <= 0:
            raise forms.ValidationError("Price has to be greater than zero.")
        return price

    def clean_erp_id(self):
        erp_id = (self.cleaned_data.get("erp_id") or "").strip()
        return erp_id or None  # empty -> None, so several books without ERP ID are allowed
