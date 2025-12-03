from django.apps import AppConfig

class TodoPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.todo_panel'

    def ready(self):
        from django.conf import settings
        print(f"🔑 SECRET_KEY actual (primeros 5 chars): {settings.SECRET_KEY[:5]}...")
