from django.urls import path

from apps.assignments.views import (
    assignment_dashboard_view,
    assign_submit_view,
    transfer_owner_submit_view,
    return_submit_view,
    transfer_submit_view,
)

urlpatterns = [
    path("", assignment_dashboard_view, name="assignment-dashboard"),
    path("actions/assign/", assign_submit_view, name="assignment-assign-submit"),
    path(
        "actions/<int:assignment_id>/return/",
        return_submit_view,
        name="assignment-return-submit",
    ),
    path(
        "actions/<int:assignment_id>/transfer/",
        transfer_submit_view,
        name="assignment-transfer-submit",
    ),
    path(
        "actions/assets/<int:asset_id>/transfer-owner/",
        transfer_owner_submit_view,
        name="asset-transfer-owner-submit",
    ),
]
