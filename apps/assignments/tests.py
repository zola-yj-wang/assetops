from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.assignments.models import Assignment
from apps.assignments.services import (
    assign_asset,
    offboarding_check,
    return_asset,
    transfer_asset,
)
from apps.assets.models import Asset
from apps.employees.models import Employee


class AssignmentServiceTestCase(TestCase):
    def setUp(self):
        self.employee_active = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.employee_inactive = Employee.objects.create(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            employment_status=Employee.EmploymentStatus.INACTIVE,
        )
        self.employee_target = Employee.objects.create(
            first_name="Linus",
            last_name="Torvalds",
            email="linus@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.asset = Asset.objects.create(
            asset_tag="LT-001",
            serial_number="SN-LT-001",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )

    def test_assign_asset_creates_active_assignment_and_updates_asset_status(self):
        assignment = assign_asset(
            employee=self.employee_active,
            asset=self.asset,
            notes="First issue",
        )

        self.asset.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.AssignmentStatus.ASSIGNED)
        self.assertEqual(self.asset.status, Asset.AssetStatus.ASSIGNED)

    def test_assign_asset_rejects_non_stock_asset(self):
        self.asset.status = Asset.AssetStatus.IN_REPAIR
        self.asset.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ValidationError) as exc:
            assign_asset(employee=self.employee_active, asset=self.asset)
        self.assertIn(
            "This asset is not in stock and cannot be assigned.",
            exc.exception.message_dict["asset"],
        )

    def test_assign_asset_rejects_inactive_employee(self):
        with self.assertRaises(ValidationError) as exc:
            assign_asset(employee=self.employee_inactive, asset=self.asset)
        self.assertIn(
            "Only onboarding or active employees can receive assets.",
            exc.exception.message_dict["employee"],
        )

    def test_assign_asset_rejects_double_assignment_with_clear_message(self):
        assign_asset(employee=self.employee_active, asset=self.asset)

        with self.assertRaises(ValidationError) as exc:
            assign_asset(employee=self.employee_active, asset=self.asset)

        self.assertIn(
            "This asset is already assigned and cannot be assigned twice.",
            exc.exception.message_dict["asset"],
        )

    def test_return_asset_marks_assignment_returned_and_asset_in_stock(self):
        assignment = assign_asset(employee=self.employee_active, asset=self.asset)

        updated = return_asset(assignment=assignment, notes="Returned in good condition")

        self.asset.refresh_from_db()
        self.assertEqual(updated.status, Assignment.AssignmentStatus.RETURNED)
        self.assertEqual(self.asset.status, Asset.AssetStatus.IN_STOCK)

    def test_return_asset_rejects_non_active_assignment(self):
        assignment = assign_asset(employee=self.employee_active, asset=self.asset)
        return_asset(assignment=assignment)

        with self.assertRaises(ValidationError) as exc:
            return_asset(assignment=assignment)
        self.assertIn(
            "This assignment is already returned or inactive and cannot be returned again.",
            exc.exception.message_dict["status"],
        )

    def test_offboarding_check_blocks_employee_with_active_assets(self):
        assign_asset(employee=self.employee_active, asset=self.asset)

        result = offboarding_check(employee=self.employee_active)

        self.assertFalse(result["can_offboard"])
        self.assertEqual(result["active_assignment_count"], 1)

    def test_offboarding_check_allows_employee_after_return(self):
        assignment = assign_asset(employee=self.employee_active, asset=self.asset)
        return_asset(assignment=assignment)

        result = offboarding_check(employee=self.employee_active)

        self.assertTrue(result["can_offboard"])
        self.assertEqual(result["active_assignment_count"], 0)

    def test_transfer_asset_returns_old_and_creates_new_assignment(self):
        original = assign_asset(employee=self.employee_active, asset=self.asset)

        transferred = transfer_asset(
            assignment=original,
            to_employee=self.employee_target,
            notes="Owner changed",
        )

        original.refresh_from_db()
        self.asset.refresh_from_db()
        self.assertEqual(original.status, Assignment.AssignmentStatus.RETURNED)
        self.assertEqual(transferred.status, Assignment.AssignmentStatus.ASSIGNED)
        self.assertEqual(transferred.employee_id, self.employee_target.id)
        self.assertEqual(transferred.asset_id, self.asset.id)
        self.assertEqual(self.asset.status, Asset.AssetStatus.ASSIGNED)

    def test_transfer_asset_rejects_inactive_target_employee(self):
        original = assign_asset(employee=self.employee_active, asset=self.asset)

        with self.assertRaises(ValidationError) as exc:
            transfer_asset(
                assignment=original,
                to_employee=self.employee_inactive,
                notes="move",
            )

        self.assertIn(
            "Only onboarding or active employees can receive assets.",
            exc.exception.message_dict["employee"],
        )

    def test_transfer_asset_rejects_same_employee(self):
        original = assign_asset(employee=self.employee_active, asset=self.asset)

        with self.assertRaises(ValidationError) as exc:
            transfer_asset(
                assignment=original,
                to_employee=self.employee_active,
            )

        self.assertIn(
            "Transfer target must be a different employee.",
            exc.exception.message_dict["employee"],
        )

    def test_transfer_asset_rejects_non_active_assignment(self):
        original = assign_asset(employee=self.employee_active, asset=self.asset)
        return_asset(assignment=original)

        with self.assertRaises(ValidationError) as exc:
            transfer_asset(
                assignment=original,
                to_employee=self.employee_target,
            )

        self.assertIn(
            "Only active assignments can be transferred.",
            exc.exception.message_dict["status"],
        )


class AssignmentModelValidationTestCase(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Alan",
            last_name="Turing",
            email="alan@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.asset = Asset.objects.create(
            asset_tag="LT-002",
            serial_number="SN-LT-002",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )

    def test_cannot_create_assignment_directly_as_returned(self):
        assignment = Assignment(
            employee=self.employee,
            asset=self.asset,
            status=Assignment.AssignmentStatus.RETURNED,
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_returned_assignment_cannot_be_reopened(self):
        assignment = assign_asset(employee=self.employee, asset=self.asset)
        return_asset(assignment=assignment)

        assignment.status = Assignment.AssignmentStatus.ASSIGNED
        with self.assertRaises(ValidationError):
            assignment.full_clean()


class AssignmentApiErrorMessageTestCase(TestCase):
    def test_assign_api_returns_clear_error_for_invalid_json(self):
        response = self.client.post(
            reverse("assignment-assign"),
            data="{invalid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["payload"][0],
            "Invalid JSON payload.",
        )

    def test_assign_api_returns_clear_error_for_missing_required_ids(self):
        response = self.client.post(
            reverse("assignment-assign"),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["employee"][0],
            "employee_id is required.",
        )

    def test_transfer_api_returns_clear_error_for_missing_target(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada-transfer@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        asset = Asset.objects.create(
            asset_tag="LT-API-1",
            serial_number="SN-LT-API-1",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )
        assignment = assign_asset(employee=employee, asset=asset)

        response = self.client.post(
            reverse("assignment-transfer", kwargs={"assignment_id": assignment.id}),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["employee"][0],
            "to_employee_id is required.",
        )


class AssignmentWebTransferTestCase(TestCase):
    def setUp(self):
        self.from_employee = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada-web@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.to_employee = Employee.objects.create(
            first_name="Linus",
            last_name="Torvalds",
            email="linus-web@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.asset = Asset.objects.create(
            asset_tag="LT-WEB-1",
            serial_number="SN-LT-WEB-1",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )
        self.assignment = assign_asset(employee=self.from_employee, asset=self.asset)

    def test_transfer_submit_view_moves_owner_from_asset_list(self):
        response = self.client.post(
            reverse(
                "asset-transfer-owner-submit",
                kwargs={"asset_id": self.asset.id},
            ),
            data={"to_employee_id": self.to_employee.id, "notes": "handover"},
            follow=False,
        )

        self.assertRedirects(response, reverse("asset-list"), fetch_redirect_response=False)

        self.assignment.refresh_from_db()
        self.asset.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.AssignmentStatus.RETURNED)

        new_assignment = Assignment.objects.get(
            asset=self.asset,
            status=Assignment.AssignmentStatus.ASSIGNED,
        )
        self.assertEqual(new_assignment.employee_id, self.to_employee.id)
        self.assertEqual(self.asset.status, Asset.AssetStatus.ASSIGNED)

    def test_transfer_owner_submit_assigns_in_stock_asset(self):
        in_stock_asset = Asset.objects.create(
            asset_tag="LT-WEB-2",
            serial_number="SN-LT-WEB-2",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )

        response = self.client.post(
            reverse(
                "asset-transfer-owner-submit",
                kwargs={"asset_id": in_stock_asset.id},
            ),
            data={"to_employee_id": self.to_employee.id, "notes": "direct owner setup"},
            follow=False,
        )

        self.assertRedirects(response, reverse("asset-list"), fetch_redirect_response=False)
        in_stock_asset.refresh_from_db()
        self.assertEqual(in_stock_asset.status, Asset.AssetStatus.ASSIGNED)

        new_assignment = Assignment.objects.get(
            asset=in_stock_asset,
            status=Assignment.AssignmentStatus.ASSIGNED,
        )
        self.assertEqual(new_assignment.employee_id, self.to_employee.id)
