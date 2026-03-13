from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import assetops_operator_required
from apps.accounts.services import notify_default_admin_group_for_change
from apps.assignments.models import Assignment
from apps.assets.forms import AssetForm, AssetTypeForm
from apps.assets.models import Asset, AssetType
from apps.employees.models import Employee


@assetops_operator_required
def asset_list_view(request):
    selected_asset_types = request.GET.getlist("asset_type")
    valid_asset_types = set(AssetType.objects.values_list("id", flat=True))
    selected_asset_types = [
        asset_type
        for asset_type in selected_asset_types
        if asset_type.isdigit() and int(asset_type) in valid_asset_types
    ]

    assets = Asset.objects.select_related("asset_type").order_by("asset_tag")
    if selected_asset_types:
        assets = assets.filter(asset_type_id__in=selected_asset_types)
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
        "asset_type_choices": AssetType.objects.order_by("name"),
        "physical_location_choices": Asset.PhysicalLocation.choices,
        "selected_asset_types": selected_asset_types,
    }
    return render(request, "assets/list.html", context)


@assetops_operator_required
def asset_create_view(request):
    if request.method == "POST":
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save()
            notify_default_admin_group_for_change(
                actor=request.user,
                resource_type="asset",
                action="create",
                object_label=asset.asset_tag,
                object_instance=asset,
            )
            messages.success(request, "Asset created successfully.")
            return redirect("asset-list")
    else:
        form = AssetForm()

    return render(
        request,
        "assets/form.html",
        {
            "form": form,
            "page_title": "Create Asset",
            "submit_label": "Create Asset",
            "asset_type_manage_url": "asset-type-list",
        },
    )


@assetops_operator_required
def asset_update_view(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    if request.method == "POST":
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            asset = form.save()
            notify_default_admin_group_for_change(
                actor=request.user,
                resource_type="asset",
                action="update",
                object_label=asset.asset_tag,
                object_instance=asset,
            )
            messages.success(request, "Asset updated successfully.")
            return redirect("asset-list")
    else:
        form = AssetForm(instance=asset)

    return render(
        request,
        "assets/form.html",
        {
            "form": form,
            "page_title": "Edit Asset",
            "submit_label": "Save Changes",
            "asset_type_manage_url": "asset-type-list",
        },
    )


@require_POST
@assetops_operator_required
def asset_delete_view(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    has_active_assignment = Assignment.objects.filter(
        asset=asset,
        status=Assignment.AssignmentStatus.ASSIGNED,
    ).exists()
    if has_active_assignment:
        messages.error(request, "Cannot delete an asset with an active assignment.")
        return redirect("asset-list")

    asset_label = asset.asset_tag
    asset.delete()
    notify_default_admin_group_for_change(
        actor=request.user,
        resource_type="asset",
        action="delete",
        object_label=asset_label,
        object_instance=asset,
    )
    messages.success(request, "Asset deleted successfully.")
    return redirect("asset-list")


@assetops_operator_required
def asset_type_list_view(request):
    asset_types = AssetType.objects.select_related("default_admin_group").order_by("name")
    return render(request, "assets/type_list.html", {"asset_types": asset_types})


@assetops_operator_required
def asset_type_create_view(request):
    if request.method == "POST":
        form = AssetTypeForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Asset type created successfully.")
            return redirect("asset-type-list")
    else:
        form = AssetTypeForm(user=request.user)

    return render(
        request,
        "assets/type_form.html",
        {"form": form, "page_title": "Create Asset Type", "submit_label": "Create Asset Type"},
    )


@assetops_operator_required
def asset_type_update_view(request, asset_type_id):
    asset_type = get_object_or_404(AssetType, pk=asset_type_id)
    if request.method == "POST":
        form = AssetTypeForm(request.POST, instance=asset_type, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Asset type updated successfully.")
            return redirect("asset-type-list")
    else:
        form = AssetTypeForm(instance=asset_type, user=request.user)

    return render(
        request,
        "assets/type_form.html",
        {"form": form, "page_title": "Edit Asset Type", "submit_label": "Save Changes"},
    )


@require_POST
@assetops_operator_required
def asset_type_delete_view(request, asset_type_id):
    asset_type = get_object_or_404(AssetType, pk=asset_type_id)
    if asset_type.assets.exists():
        messages.error(request, "Cannot delete an asset type that is still in use.")
        return redirect("asset-type-list")

    asset_type.delete()
    messages.success(request, "Asset type deleted successfully.")
    return redirect("asset-type-list")
