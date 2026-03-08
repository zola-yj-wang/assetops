from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.assignments.models import Assignment
from apps.assignments.services import assign_asset, offboarding_check, return_asset
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

        with self.assertRaises(ValidationError):
            assign_asset(employee=self.employee_active, asset=self.asset)

    def test_assign_asset_rejects_inactive_employee(self):
        with self.assertRaises(ValidationError):
            assign_asset(employee=self.employee_inactive, asset=self.asset)

    def test_return_asset_marks_assignment_returned_and_asset_in_stock(self):
        assignment = assign_asset(employee=self.employee_active, asset=self.asset)

        updated = return_asset(assignment=assignment, notes="Returned in good condition")

        self.asset.refresh_from_db()
        self.assertEqual(updated.status, Assignment.AssignmentStatus.RETURNED)
        self.assertEqual(self.asset.status, Asset.AssetStatus.IN_STOCK)

    def test_return_asset_rejects_non_active_assignment(self):
        assignment = assign_asset(employee=self.employee_active, asset=self.asset)
        return_asset(assignment=assignment)

        with self.assertRaises(ValidationError):
            return_asset(assignment=assignment)

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
