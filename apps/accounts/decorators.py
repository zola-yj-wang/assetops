from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

from apps.accounts.services import user_can_access_assetops


def assetops_operator_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            if request.path.startswith("/api/"):
                return HttpResponseForbidden("Authentication required.")
            return redirect_to_login(request.get_full_path())
        if user_can_access_assetops(request.user):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("AssetOps access requires an IT, OM, HR, or FIN group.")

    return wrapped
