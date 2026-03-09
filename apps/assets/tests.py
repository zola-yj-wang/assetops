from django.test import TestCase
from django.urls import reverse

from apps.assignments.services import assign_asset
from apps.assets.models import Asset
from apps.employees.models import Employee


class AssetListPageTestCase(TestCase):
    def test_asset_list_page_renders(self):
        Asset.objects.create(
            asset_tag="LT-PAGE-1",
            serial_number="SN-PAGE-1",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )

        response = self.client.get(reverse("asset-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Asset List")
        self.assertContains(response, "LT-PAGE-1")

    def test_asset_list_shows_transfer_form_for_assigned_asset(self):
        employee_1 = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada-asset@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        Employee.objects.create(
            first_name="Linus",
            last_name="Torvalds",
            email="linus-asset@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        asset = Asset.objects.create(
            asset_tag="LT-PAGE-2",
            serial_number="SN-PAGE-2",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )
        assignment = assign_asset(employee=employee_1, asset=asset)

        response = self.client.get(reverse("asset-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                "asset-transfer-owner-submit",
                kwargs={"asset_id": assignment.asset_id},
            ),
        )


class AssetCrudPageTestCase(TestCase):
    def test_asset_create_update_delete_flow(self):
        create_response = self.client.post(
            reverse("asset-create"),
            data={
                "asset_tag": "LT-CRUD-1",
                "serial_number": "SN-CRUD-1",
                "asset_type": Asset.AssetType.LAPTOP,
                "brand": "Dell",
                "model": "XPS",
                "purchase_date": "",
                "purchase_cost": "",
                "depreciation_months": 36,
                "status": Asset.AssetStatus.IN_STOCK,
                "notes": "new asset",
            },
            follow=False,
        )
        self.assertRedirects(create_response, reverse("asset-list"), fetch_redirect_response=False)

        asset = Asset.objects.get(asset_tag="LT-CRUD-1")
        update_response = self.client.post(
            reverse("asset-update", kwargs={"asset_id": asset.id}),
            data={
                "asset_tag": "LT-CRUD-1",
                "serial_number": "SN-CRUD-1",
                "asset_type": Asset.AssetType.LAPTOP,
                "brand": "Lenovo",
                "model": "T14",
                "purchase_date": "",
                "purchase_cost": "",
                "depreciation_months": 36,
                "status": Asset.AssetStatus.IN_STOCK,
                "notes": "updated asset",
            },
            follow=False,
        )
        self.assertRedirects(update_response, reverse("asset-list"), fetch_redirect_response=False)

        asset.refresh_from_db()
        self.assertEqual(asset.brand, "Lenovo")
        self.assertEqual(asset.model, "T14")

        delete_response = self.client.post(
            reverse("asset-delete", kwargs={"asset_id": asset.id}),
            follow=False,
        )
        self.assertRedirects(delete_response, reverse("asset-list"), fetch_redirect_response=False)
        self.assertFalse(Asset.objects.filter(id=asset.id).exists())
