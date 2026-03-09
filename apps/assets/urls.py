from django.urls import path

from apps.assets.views import (
    asset_create_view,
    asset_delete_view,
    asset_list_view,
    asset_update_view,
)

urlpatterns = [
    path("", asset_list_view, name="asset-list"),
    path("create/", asset_create_view, name="asset-create"),
    path("<int:asset_id>/edit/", asset_update_view, name="asset-update"),
    path("<int:asset_id>/delete/", asset_delete_view, name="asset-delete"),
]
