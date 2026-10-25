from django.urls import path

from . import views

app_name = "erp_import"

urlpatterns = [
    path("upload/", views.upload, name="upload"),
]
