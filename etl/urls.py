from django.urls import path
from . import views
urlpatterns = [
    path("", views.upload_view, name="upload"),
    path("preview/", views.preview_view, name="preview"),
    path("mapping/", views.mapping_view, name="mapping"),
    path("rules/", views.rules_view, name="rules"),
    path("process/", views.process_view, name="process"),
    path("done/", views.done_view, name="done"),
]