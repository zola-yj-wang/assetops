from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import send_mail

from apps.accounts.constants import DEFAULT_ADMIN_GROUP_BY_RESOURCE, OPERATOR_GROUPS


def user_can_access_assetops(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=OPERATOR_GROUPS).exists()


def user_group_names(user) -> list[str]:
    if not getattr(user, "is_authenticated", False):
        return []
    return list(user.groups.filter(name__in=OPERATOR_GROUPS).values_list("name", flat=True))


def get_default_admin_group(resource_type: str, object_instance=None) -> str:
    if resource_type == "employee":
        return DEFAULT_ADMIN_GROUP_BY_RESOURCE[resource_type]

    if resource_type == "asset":
        asset_type = getattr(object_instance, "asset_type", None)
        default_admin_group = getattr(asset_type, "default_admin_group", None)
        return getattr(default_admin_group, "name", "OM")

    if resource_type == "assignment":
        asset = getattr(object_instance, "asset", None)
        asset_type = getattr(asset, "asset_type", None)
        default_admin_group = getattr(asset_type, "default_admin_group", None)
        return getattr(default_admin_group, "name", "OM")

    raise KeyError(f"Unsupported resource type: {resource_type}")


def notify_default_admin_group_for_change(
    *,
    actor,
    resource_type: str,
    action: str,
    object_label: str,
    object_instance=None,
) -> int:
    if not getattr(actor, "is_authenticated", False) or actor.is_superuser:
        return 0

    admin_group_name = get_default_admin_group(resource_type, object_instance)
    actor_groups = set(user_group_names(actor))
    if admin_group_name in actor_groups:
        return 0

    recipients = list(
        get_user_model()
        .objects.filter(groups__name=admin_group_name, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients:
        return 0

    actor_label = actor.get_full_name() or actor.get_username()
    actor_groups_text = ", ".join(sorted(actor_groups)) if actor_groups else "no operator group"
    subject = f"[AssetOps] {resource_type} {action}: notify {admin_group_name}"
    message = (
        f"{actor_label} ({actor_groups_text}) performed {action} on {resource_type} "
        f"record {object_label}.\n"
        f"Default admin group: {admin_group_name}."
    )
    return send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "assetops@example.com"),
        recipient_list=recipients,
        fail_silently=True,
    )


def ensure_operator_groups() -> None:
    for group_name in OPERATOR_GROUPS:
        Group.objects.get_or_create(name=group_name)
