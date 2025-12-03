from django.urls import path
from . import views
from .health import health_check

app_name = 'todo_panel'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/auth/initiate/', views.initiate_auth, name='initiate_auth'),
    path('api/auth/check/', views.check_auth_status, name='check_auth_status'),
    path('health/', health_check, name='health_check'),
]
