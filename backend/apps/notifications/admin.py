from django.contrib import admin

from apps.core.readonly_admin import ReadOnlyAdmin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = ("user", "message_code", "kind", "channel", "status", "created_at", "read_at")
    list_filter = ("kind", "status", "channel")
    search_fields = ("user__phone", "message_code")
