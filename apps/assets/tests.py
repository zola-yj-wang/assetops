from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.assignments.services import assign_asset
from apps.assets.models import Asset, AssetType
from apps.employees.models import Employee


def get_asset_type(code):
    return AssetType.objects.get(code=code)


class AssetOperatorAccessMixin:
    operator_group = "IT"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username=f"{self.operator_group.lower()}-operator",
            email=f"{self.operator_group.lower()}-operator@example.com",
            password="password123",
        )
        operator_group, _ = Group.objects.get_or_create(name=self.operator_group)
        self.user.groups.add(operator_group)
        self.client.force_login(self.user)


class AssetListPageTestCase(AssetOperatorAccessMixin, TestCase):
    def test_asset_list_page_renders(self):
        Asset.objects.create(
            asset_tag="LT-PAGE-1",
            serial_number="SN-PAGE-1",
            asset_type=get_asset_type(Asset.AssetType.LAPTOP),
            status=Asset.AssetStatus.IN_STOCK,
            physical_location=Asset.PhysicalLocation.IT_ROOM,
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
            asset_type=get_asset_type(Asset.AssetType.LAPTOP),
            status=Asset.AssetStatus.IN_STOCK,
            physical_location=Asset.PhysicalLocation.IT_ROOM,
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

    def test_asset_list_can_filter_by_multiple_asset_types(self):
        Asset.objects.create(
            asset_tag="LT-FILTER-1",
            serial_number="SN-FILTER-1",
            asset_type=get_asset_type(Asset.AssetType.LAPTOP),
            status=Asset.AssetStatus.IN_STOCK,
            physical_location=Asset.PhysicalLocation.IT_ROOM,
        )
        Asset.objects.create(
            asset_tag="MN-FILTER-1",
            serial_number="SN-FILTER-2",
            asset_type=get_asset_type(Asset.AssetType.MONITOR),
            status=Asset.AssetStatus.IN_STOCK,
            physical_location=Asset.PhysicalLocation.SERVER_ROOM,
        )
        Asset.objects.create(
            asset_tag="PH-FILTER-1",
            serial_number="SN-FILTER-3",
            asset_type=get_asset_type(Asset.AssetType.PHONE),
            status=Asset.AssetStatus.IN_STOCK,
            physical_location=Asset.PhysicalLocation.OTHER,
        )

        response = self.client.get(
            reverse("asset-list"),
            {
                "asset_type": [
                    get_asset_type(Asset.AssetType.LAPTOP).id,
                    get_asset_type(Asset.AssetType.MONITOR).id,
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LT-FILTER-1")
        self.assertContains(response, "MN-FILTER-1")
        self.assertNotContains(response, "PH-FILTER-1")


class AssetCrudPageTestCase(AssetOperatorAccessMixin, TestCase):
    def test_asset_create_update_delete_flow(self):
        create_response = self.client.post(
            reverse("asset-create"),
            data={
                "asset_tag": "LT-CRUD-1",
                "serial_number": "SN-CRUD-1",
                "asset_type": get_asset_type(Asset.AssetType.LAPTOP).id,
                "brand": "Dell",
                "model": "XPS",
                "purchase_date": "",
                "purchase_cost": "",
                "depreciation_months": 36,
                "status": Asset.AssetStatus.IN_STOCK,
                "physical_location": Asset.PhysicalLocation.IT_ROOM,
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
                "asset_type": get_asset_type(Asset.AssetType.LAPTOP).id,
                "brand": "Lenovo",
                "model": "T14",
                "purchase_date": "",
                "purchase_cost": "",
                "depreciation_months": 36,
                "status": Asset.AssetStatus.IN_STOCK,
                "physical_location": Asset.PhysicalLocation.SERVER_ROOM,
                "notes": "updated asset",
            },
            follow=False,
        )
        self.assertRedirects(update_response, reverse("asset-list"), fetch_redirect_response=False)

        asset.refresh_from_db()
        self.assertEqual(asset.brand, "Lenovo")
        self.assertEqual(asset.model, "T14")
        self.assertEqual(asset.physical_location, Asset.PhysicalLocation.SERVER_ROOM)

        delete_response = self.client.post(
            reverse("asset-delete", kwargs={"asset_id": asset.id}),
            follow=False,
        )
        self.assertRedirects(delete_response, reverse("asset-list"), fetch_redirect_response=False)
        self.assertFalse(Asset.objects.filter(id=asset.id).exists())

    def test_non_owner_group_change_sends_notification_to_asset_type_admin_group(self):
        hr_group, _ = Group.objects.get_or_create(name="HR")
        hr_user = User.objects.create_user(
            username="hr-admin",
            email="hr-admin@example.com",
            password="password123",
        )
        hr_user.groups.add(hr_group)

        fin_group, _ = Group.objects.get_or_create(name="FIN")
        self.user.groups.clear()
        self.user.groups.add(fin_group)

        response = self.client.post(
            reverse("asset-create"),
            data={
                "asset_tag": "LT-NOTIFY-1",
                "serial_number": "SN-NOTIFY-1",
                "asset_type": get_asset_type(Asset.AssetType.BADGE).id,
                "brand": "Dell",
                "model": "XPS",
                "purchase_date": "",
                "purchase_cost": "",
                "depreciation_months": 36,
                "status": Asset.AssetStatus.IN_STOCK,
                "physical_location": Asset.PhysicalLocation.RECEPTION,
                "notes": "notify HR",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["hr-admin@example.com"])

    def test_anonymous_user_cannot_access_asset_pages(self):
        self.client.logout()
        response = self.client.get(reverse("asset-list"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('asset-list')}",
            fetch_redirect_response=False,
        )


class AssetModelValidationTestCase(TestCase):
    def test_in_stock_asset_requires_physical_location(self):
        asset = Asset(
            asset_tag="LT-VALID-1",
            serial_number="SN-VALID-1",
            asset_type=get_asset_type(Asset.AssetType.LAPTOP),
            status=Asset.AssetStatus.IN_STOCK,
            physical_location="",
        )
        with self.assertRaises(ValidationError):
            asset.full_clean()


class AssetTypeCrudPageTestCase(AssetOperatorAccessMixin, TestCase):
    def test_asset_type_create_update_delete_flow(self):
        it_group = Group.objects.get(name="IT")
        create_response = self.client.post(
            reverse("asset-type-create"),
            data={"name": "Docking Station", "default_admin_group": it_group.id},
            follow=False,
        )
        self.assertRedirects(
            create_response,
            reverse("asset-type-list"),
            fetch_redirect_response=False,
        )

        asset_type = AssetType.objects.get(name="Docking Station")
        self.assertEqual(asset_type.code, "DOCKING_STATION")
        self.assertEqual(asset_type.default_admin_group.name, "IT")

        update_response = self.client.post(
            reverse("asset-type-update", kwargs={"asset_type_id": asset_type.id}),
            data={"name": "Docking Station", "default_admin_group": it_group.id},
            follow=False,
        )
        self.assertRedirects(
            update_response,
            reverse("asset-type-list"),
            fetch_redirect_response=False,
        )

        asset_type.refresh_from_db()
        self.assertEqual(asset_type.default_admin_group.name, "IT")

        delete_response = self.client.post(
            reverse("asset-type-delete", kwargs={"asset_type_id": asset_type.id}),
            follow=False,
        )
        self.assertRedirects(
            delete_response,
            reverse("asset-type-list"),
            fetch_redirect_response=False,
        )
        self.assertFalse(AssetType.objects.filter(id=asset_type.id).exists())

    def test_asset_type_create_requires_default_group(self):
        response = self.client.post(
            reverse("asset-type-create"),
            data={"name": "Printer"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")

    def test_asset_type_create_cannot_assign_group_outside_user_membership(self):
        hr_group = Group.objects.get(name="HR")
        response = self.client.post(
            reverse("asset-type-create"),
            data={"name": "Printer", "default_admin_group": hr_group.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "You can only assign an asset type to a group you belong to.",
        )
        self.assertFalse(AssetType.objects.filter(name="Printer").exists())

    def test_asset_type_form_only_shows_user_groups(self):
        response = self.client.get(reverse("asset-type-create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ">IT</option>")
        self.assertNotContains(response, ">HR</option>")
        self.assertNotContains(response, ">OM</option>")
        self.assertNotContains(response, ">FIN</option>")
