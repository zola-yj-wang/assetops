from django.urls import path

from apps.assets.views import (
    asset_create_view,
    asset_delete_view,
    asset_list_view,
    asset_type_create_view,
    asset_type_delete_view,
    asset_type_list_view,
    asset_type_update_view,
    asset_update_view,
)

urlpatterns = [
    path("", asset_list_view, name="asset-list"),
    path("types/", asset_type_list_view, name="asset-type-list"),
    path("types/create/", asset_type_create_view, name="asset-type-create"),
    path("types/<int:asset_type_id>/edit/", asset_type_update_view, name="asset-type-update"),
    path("types/<int:asset_type_id>/delete/", asset_type_delete_view, name="asset-type-delete"),
    path("create/", asset_create_view, name="asset-create"),
    path("<int:asset_id>/edit/", asset_update_view, name="asset-update"),
    path("<int:asset_id>/delete/", asset_delete_view, name="asset-delete"),
]
