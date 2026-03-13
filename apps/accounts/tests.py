from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services import (
    ensure_operator_groups,
    get_default_admin_group,
    user_can_access_assetops,
)
from apps.assets.models import Asset
from apps.assets.models import AssetType
from apps.employees.models import Employee
from apps.assignments.models import Assignment


def get_asset_type(code):
    return AssetType.objects.get(code=code)


class AssetOpsGroupServiceTestCase(TestCase):
    def test_ensure_operator_groups_creates_expected_groups(self):
        ensure_operator_groups()
        self.assertEqual(Group.objects.filter(name__in=["IT", "OM", "HR", "FIN"]).count(), 4)

    def test_user_in_operator_group_can_access_assetops(self):
        user = User.objects.create_user(username="operator", password="password123")
        group, _ = Group.objects.get_or_create(name="IT")
        user.groups.add(group)

        self.assertTrue(user_can_access_assetops(user))

    def test_user_without_operator_group_cannot_access_assetops(self):
        user = User.objects.create_user(username="plain-user", password="password123")
        self.assertFalse(user_can_access_assetops(user))

    def test_asset_admin_group_is_resolved_by_asset_type(self):
        asset = Asset(
            asset_tag="BADGE-1",
            serial_number="SN-BADGE-1",
            asset_type=get_asset_type(Asset.AssetType.BADGE),
        )
        self.assertEqual(get_default_admin_group("asset", asset), "HR")

    def test_assignment_admin_group_follows_asset_type(self):
        employee = Employee.objects.create(
            first_name="Test",
            last_name="User",
            email="assignment-owner@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        asset = Asset.objects.create(
            asset_tag="PHONE-1",
            serial_number="SN-PHONE-1",
            asset_type=get_asset_type(Asset.AssetType.PHONE),
            status=Asset.AssetStatus.IN_STOCK,
        )
        assignment = Assignment.objects.create(employee=employee, asset=asset)
        self.assertEqual(get_default_admin_group("assignment", assignment), "OM")

    def test_employee_admin_group_is_always_hr(self):
        employee = Employee.objects.create(
            first_name="HR",
            last_name="Owner",
            email="hr-owner@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.assertEqual(get_default_admin_group("employee", employee), "HR")


class AuthenticationPageTestCase(TestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AssetOps Login")

    def test_login_redirects_operator_to_dashboard(self):
        user = User.objects.create_user(username="operator", password="password123")
        group, _ = Group.objects.get_or_create(name="IT")
        user.groups.add(group)

        response = self.client.post(
            reverse("login"),
            data={"username": "operator", "password": "password123"},
            follow=False,
        )
        self.assertRedirects(
            response,
            reverse("assignment-dashboard"),
            fetch_redirect_response=False,
        )

    def test_logout_clears_session(self):
        user = User.objects.create_user(username="operator", password="password123")
        group, _ = Group.objects.get_or_create(name="IT")
        user.groups.add(group)
        self.client.force_login(user)

        response = self.client.post(reverse("logout"), follow=False)
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)

        protected = self.client.get(reverse("asset-list"), follow=False)
        self.assertRedirects(
            protected,
            f"{reverse('login')}?next={reverse('asset-list')}",
            fetch_redirect_response=False,
        )
