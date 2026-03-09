from django import forms

from apps.assets.models import Asset


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "asset_tag",
            "serial_number",
            "asset_type",
            "brand",
            "model",
            "purchase_date",
            "purchase_cost",
            "depreciation_months",
            "status",
            "notes",
        ]
