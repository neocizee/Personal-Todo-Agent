from django.urls import path
from . import views, health

app_name = 'todo_panel'

urlpatterns = [
    # Vistas de UI
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('redis-test/', views.redis_test, name='redis_test'),
    
    # API Endpoints para autenticación
    path('api/auth/initiate/', views.initiate_auth, name='initiate_auth'),
    path('api/auth/check-status/', views.check_auth_status, name='check_auth_status'),
    
    # Health Check
    path('health/', health.health_check, name='health_check'),
]
