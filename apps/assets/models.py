from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.accounts.constants import OPERATOR_GROUPS


class AssetType(models.Model):
    code = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    default_admin_group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="managed_asset_types",
        limit_choices_to=models.Q(name__in=OPERATOR_GROUPS),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        generated_code = slugify(self.name).replace("-", "_").upper()
        if not generated_code:
            raise ValidationError({"name": "Asset type name must contain letters or numbers."})
        self.code = generated_code

        if self.default_admin_group_id and self.default_admin_group.name not in OPERATOR_GROUPS:
            raise ValidationError(
                {"default_admin_group": "Default admin group must be IT, OM, HR, or FIN."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def get_default_asset_type_pk():
    asset_type = AssetType.objects.filter(code=Asset.AssetType.OTHER).first()
    if asset_type is None:
        raise AssetType.DoesNotExist("Default asset type OTHER is not configured.")
    return asset_type.pk


class AssetTypeCode(models.TextChoices):
    LAPTOP = "LAPTOP", "Laptop"
    MONITOR = "MONITOR", "Monitor"
    PHONE = "PHONE", "Phone"
    BADGE = "BADGE", "Badge"
    HEADSET = "HEADSET", "Headset"
    KEYBOARD = "KEYBOARD", "Keyboard"
    OTHER = "OTHER", "Other"


class Asset(models.Model):
    AssetType = AssetTypeCode

    class AssetStatus(models.TextChoices):
        IN_STOCK = "IN_STOCK", "In stock"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_REPAIR = "IN_REPAIR", "In repair"
        RETIRED = "RETIRED", "Retired"
        LOST = "LOST", "Lost"

    class PhysicalLocation(models.TextChoices):
        IT_ROOM = "IT_ROOM", "IT room"
        SERVER_ROOM = "SERVER_ROOM", "Server room"
        RECEPTION = "RECEPTION", "Reception"
        WITH_OWNER = "WITH_OWNER", "With owner"
        OTHER = "OTHER", "Other"

    asset_tag = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100, unique=True)
    asset_type = models.ForeignKey(
        "assets.AssetType",
        on_delete=models.PROTECT,
        related_name="assets",
        default=get_default_asset_type_pk,
    )
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    depreciation_months = models.PositiveIntegerField(default=36)
    status = models.CharField(
        max_length=20,
        choices=AssetStatus.choices,
        default=AssetStatus.IN_STOCK,
    )
    physical_location = models.CharField(
        max_length=20,
        choices=PhysicalLocation.choices,
        default=PhysicalLocation.IT_ROOM,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_tag"]

    def clean(self):
        super().clean()
        if self.status == self.AssetStatus.IN_STOCK and not self.physical_location:
            raise ValidationError(
                {"physical_location": "Physical location is required for in-stock assets."}
            )

    def __str__(self):
        return f"{self.asset_tag} ({self.asset_type.name})"
