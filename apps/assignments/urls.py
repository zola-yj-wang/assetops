from django.urls import path

from apps.assignments.views import (
    assignment_dashboard_view,
    assign_submit_view,
    assign_asset_view,
    offboarding_check_view,
    return_submit_view,
    return_asset_view,
)

urlpatterns = [
    path("", assignment_dashboard_view, name="assignment-dashboard"),
    path("actions/assign/", assign_submit_view, name="assignment-assign-submit"),
    path(
        "actions/<int:assignment_id>/return/",
        return_submit_view,
        name="assignment-return-submit",
    ),

    # API endpoints
    path("assign/", assign_asset_view, name="assignment-assign"),
    path("<int:assignment_id>/return/", return_asset_view, name="assignment-return"),
    path(
        "offboarding-check/<int:employee_id>/",
        offboarding_check_view,
        name="assignment-offboarding-check",
    ),
]
