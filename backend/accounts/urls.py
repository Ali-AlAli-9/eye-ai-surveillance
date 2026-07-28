from django.urls import path
from django.contrib.auth import views
from .views import login_view

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", views.LogoutView.as_view(http_method_names=["post"]), name="logout"),
]
