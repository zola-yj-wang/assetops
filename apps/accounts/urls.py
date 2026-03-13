from django.urls import path

from apps.accounts.views import AssetOpsLoginView, logout_view

urlpatterns = [
    path("login/", AssetOpsLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
]
