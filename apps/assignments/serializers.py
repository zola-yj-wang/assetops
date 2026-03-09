from rest_framework import serializers

from apps.assignments.models import Assignment
from apps.assets.models import Asset
from apps.employees.models import Employee


class AssignAssetRequestSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(required=False)
    asset_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if "employee_id" not in attrs:
            raise serializers.ValidationError({"employee": "employee_id is required."})
        if "asset_id" not in attrs:
            raise serializers.ValidationError({"asset": "asset_id is required."})

        employee = Employee.objects.filter(pk=attrs["employee_id"]).first()
        if employee is None:
            raise serializers.ValidationError({"employee": "Employee not found."})

        asset = Asset.objects.filter(pk=attrs["asset_id"]).first()
        if asset is None:
            raise serializers.ValidationError({"asset": "Asset not found."})

        attrs["employee"] = employee
        attrs["asset"] = asset
        return attrs


class ReturnAssetRequestSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    physical_location = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=Asset.PhysicalLocation.choices,
    )

    def validate(self, attrs):
        require_physical_location = self.context.get("require_physical_location", False)
        if require_physical_location and not attrs.get("physical_location"):
            raise serializers.ValidationError(
                {"physical_location": "Please select a physical location for returned asset."}
            )
        return attrs


class TransferAssetRequestSerializer(serializers.Serializer):
    to_employee_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if "to_employee_id" not in attrs:
            raise serializers.ValidationError({"employee": "to_employee_id is required."})

        to_employee = Employee.objects.filter(pk=attrs["to_employee_id"]).first()
        if to_employee is None:
            raise serializers.ValidationError({"employee": "Employee not found."})

        attrs["to_employee"] = to_employee
        return attrs


class AssignmentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "status", "employee_id", "asset_id"]


class OffboardingCheckResponseSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    can_offboard = serializers.BooleanField()
    active_assignment_count = serializers.IntegerField()
    active_asset_tags = serializers.ListField(child=serializers.CharField())
