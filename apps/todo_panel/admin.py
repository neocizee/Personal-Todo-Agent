from django.contrib import admin
from .models import MicrosoftUser

@admin.register(MicrosoftUser)
class MicrosoftUserAdmin(admin.ModelAdmin):
    list_display = ('client_id_hash', 'last_login', 'created_at')
    readonly_fields = ('client_id_hash', 'created_at', 'last_login')
    search_fields = ('client_id_hash',)
    ordering = ('-last_login',)
