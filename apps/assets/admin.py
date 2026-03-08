from django.contrib import admin
from apps.assets.models import Asset

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asset_tag",
        "serial_number",
        "asset_type",
        "brand",
        "model",
        "status",
        "purchase_cost",
    )

    search_fields = (
        "asset_tag",
        "serial_number",
        "brand",
        "model",
    )

    list_filter = (
        "asset_type",
        "status",
        "brand",
    )