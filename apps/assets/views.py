from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.assignments.models import Assignment
from apps.assets.forms import AssetForm
from apps.assets.models import Asset
from apps.employees.models import Employee


def asset_list_view(request):
    selected_asset_types = request.GET.getlist("asset_type")
    valid_asset_types = {choice[0] for choice in Asset.AssetType.choices}
    selected_asset_types = [
        asset_type for asset_type in selected_asset_types if asset_type in valid_asset_types
    ]

    assets = Asset.objects.order_by("asset_tag")
    if selected_asset_types:
        assets = assets.filter(asset_type__in=selected_asset_types)
    eligible_employees = list(
        Employee.objects.filter(
            employment_status__in=[
                Employee.EmploymentStatus.ACTIVE,
                Employee.EmploymentStatus.ONBOARDING,
            ]
        ).order_by("last_name", "first_name")
    )
    active_assignments = Assignment.objects.filter(
        status=Assignment.AssignmentStatus.ASSIGNED
    ).select_related("employee", "asset")
    active_assignment_by_asset_id = {
        assignment.asset_id: assignment for assignment in active_assignments
    }
    asset_rows = [
        {
            "asset": asset,
            "active_assignment": active_assignment_by_asset_id.get(asset.id),
            "can_transfer_owner": asset.status
            in (Asset.AssetStatus.IN_STOCK, Asset.AssetStatus.ASSIGNED),
            "transfer_candidates": [
                employee
                for employee in eligible_employees
                if active_assignment_by_asset_id.get(asset.id) is None
                or employee.id != active_assignment_by_asset_id[asset.id].employee_id
            ],
        }
        for asset in assets
    ]

    context = {
        "asset_rows": asset_rows,
        "asset_type_choices": Asset.AssetType.choices,
        "physical_location_choices": Asset.PhysicalLocation.choices,
        "selected_asset_types": selected_asset_types,
    }
    return render(request, "assets/list.html", context)


def asset_create_view(request):
    if request.method == "POST":
        form = AssetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Asset created successfully.")
            return redirect("asset-list")
    else:
        form = AssetForm()

    return render(
        request,
        "assets/form.html",
        {"form": form, "page_title": "Create Asset", "submit_label": "Create Asset"},
    )


def asset_update_view(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    if request.method == "POST":
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, "Asset updated successfully.")
            return redirect("asset-list")
    else:
        form = AssetForm(instance=asset)

    return render(
        request,
        "assets/form.html",
        {"form": form, "page_title": "Edit Asset", "submit_label": "Save Changes"},
    )


@require_POST
def asset_delete_view(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    has_active_assignment = Assignment.objects.filter(
        asset=asset,
        status=Assignment.AssignmentStatus.ASSIGNED,
    ).exists()
    if has_active_assignment:
        messages.error(request, "Cannot delete an asset with an active assignment.")
        return redirect("asset-list")

    asset.delete()
    messages.success(request, "Asset deleted successfully.")
    return redirect("asset-list")
