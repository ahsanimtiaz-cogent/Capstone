from django.contrib import admin

from .models import ChatSession, FollowupJob, MessageLog


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("discord_user_id", "display_name", "_stage", "updated_at")
    search_fields = ("discord_user_id", "display_name")
    readonly_fields = ("created_at", "updated_at")

    def _stage(self, obj: ChatSession) -> str:
        return obj.payload.get("stage", "")


@admin.register(FollowupJob)
class FollowupJobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "lead_id", "discord_user_id", "status", "send_at")
    list_filter = ("status",)
    search_fields = ("job_id", "lead_id", "discord_user_id")


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("discord_user_id", "intent", "stage_before", "stage_after", "created_at")
    list_filter = ("intent",)
    search_fields = ("discord_user_id",)
    readonly_fields = ("created_at", "updated_at")
