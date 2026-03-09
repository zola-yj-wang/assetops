from django.urls import path

from apps.assignments.views import (
    assign_asset_view,
    offboarding_check_view,
    return_asset_view,
    transfer_asset_view,
)

urlpatterns = [
    path("assign/", assign_asset_view, name="assignment-assign"),
    path("<int:assignment_id>/return/", return_asset_view, name="assignment-return"),
    path("<int:assignment_id>/transfer/", transfer_asset_view, name="assignment-transfer"),
    path(
        "offboarding-check/<int:employee_id>/",
        offboarding_check_view,
        name="assignment-offboarding-check",
    ),
]
