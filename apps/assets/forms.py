from django import forms
from django.contrib.auth.models import Group

from apps.accounts.constants import OPERATOR_GROUPS
from apps.accounts.services import user_group_names
from apps.assets.models import Asset, AssetType


class AssetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["asset_type"].queryset = AssetType.objects.order_by("name")

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
            "physical_location",
            "notes",
        ]


class AssetTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        allowed_group_names = OPERATOR_GROUPS
        if self.user is not None and not getattr(self.user, "is_superuser", False):
            allowed_group_names = tuple(user_group_names(self.user))
        self.fields["default_admin_group"].queryset = Group.objects.filter(
            name__in=allowed_group_names
        ).order_by("name")
        self.fields["default_admin_group"].error_messages["invalid_choice"] = (
            "You can only assign an asset type to a group you belong to."
        )

    class Meta:
        model = AssetType
        fields = ["name", "default_admin_group"]

    def clean_default_admin_group(self):
        default_admin_group = self.cleaned_data["default_admin_group"]
        if self.user is None or getattr(self.user, "is_superuser", False):
            return default_admin_group

        if default_admin_group.name not in user_group_names(self.user):
            raise forms.ValidationError(
                "You can only assign an asset type to a group you belong to."
            )
        return default_admin_group
