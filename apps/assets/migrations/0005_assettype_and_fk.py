from django.db import migrations, models
import django.db.models.deletion


def seed_asset_types(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    AssetType = apps.get_model("assets", "AssetType")

    defaults = [
        ("LAPTOP", "Laptop", "IT"),
        ("MONITOR", "Monitor", "IT"),
        ("PHONE", "Phone", "OM"),
        ("BADGE", "Badge", "HR"),
        ("HEADSET", "Headset", "IT"),
        ("KEYBOARD", "Keyboard", "IT"),
        ("OTHER", "Other", "OM"),
    ]
    for code, name, group_name in defaults:
        AssetType.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "default_admin_group_id": Group.objects.get(name=group_name).id,
            },
        )


def map_assets_to_asset_types(apps, schema_editor):
    Asset = apps.get_model("assets", "Asset")
    AssetType = apps.get_model("assets", "AssetType")

    type_ids_by_code = dict(AssetType.objects.values_list("code", "id"))
    for asset in Asset.objects.all().only("id", "asset_type"):
        asset.asset_type_ref_id = type_ids_by_code.get(asset.asset_type, type_ids_by_code["OTHER"])
        asset.save(update_fields=["asset_type_ref"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_create_assetops_groups"),
        ("assets", "0004_alter_asset_physical_location"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(editable=False, max_length=50, unique=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "default_admin_group",
                    models.ForeignKey(
                        limit_choices_to=models.Q(("name__in", ("IT", "OM", "HR", "FIN"))),
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="managed_asset_types",
                        to="auth.group",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.RunPython(seed_asset_types, migrations.RunPython.noop),
        migrations.AddField(
            model_name="asset",
            name="asset_type_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="assets.assettype",
            ),
        ),
        migrations.RunPython(map_assets_to_asset_types, migrations.RunPython.noop),
        migrations.RemoveField(model_name="asset", name="asset_type"),
        migrations.RenameField(model_name="asset", old_name="asset_type_ref", new_name="asset_type"),
        migrations.AlterField(
            model_name="asset",
            name="asset_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="assets",
                to="assets.assettype",
            ),
        ),
    ]
