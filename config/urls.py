"""
URL configuration for Personal Todo Agent project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.todo_panel.urls')),
]
