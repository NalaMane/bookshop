from django.urls import path

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.PreservingLoginView.as_view(template_name="accounts/login.html", authentication_form=LoginForm), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password/", views.PasswordChange.as_view(), name="password_change"),
    path("history/", views.purchase_history, name="history"),
]
