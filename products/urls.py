from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("books/<int:pk>/", views.product_detail, name="detail"),
    path("books/new/", views.product_create, name="create"),
    path("books/<int:pk>/edit/", views.product_edit, name="edit"),
    path("books/<int:pk>/delete/", views.product_delete, name="delete"),
]
