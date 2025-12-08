from django.urls import path
from . import views, health

app_name = 'todo_panel'

urlpatterns = [
    # Vistas de UI
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('tarea/<str:id_list>/', views.tarea, name='tarea'),
    path('export/<str:id_list>/', views.export_tasks, name='export_tasks'),
    path('attachment/<path:cache_key>/', views.serve_attachment, name='serve_attachment'),
    path('redis-test/', views.redis_test, name='redis_test'),
    
    # API Endpoints para autenticación
    path('api/auth/initiate/', views.initiate_auth, name='initiate_auth'),
    path('api/auth/check-status/', views.check_auth_status, name='check_auth_status'),
    path('api/tasks/<str:id_list>/sync/', views.start_sync_tasks, name='start_sync'),
    path('api/tasks/<str:id_list>/incremental/', views.incremental_sync, name='incremental_sync'),
    path('api/tasks/<str:id_list>/progress/', views.get_sync_progress, name='sync_progress'),
    
    # Health Check
    path('health/', health.health_check, name='health_check'),
]
