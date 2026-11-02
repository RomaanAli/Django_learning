from django.contrib import admin, messages
from django.core.management import call_command
from chatbot.models import ChatMessage, KnowledgeChunk


@admin.action(description="Rebuild Knowledge Base index (embed published courses & FAQs)")
def rebuild_knowledge_chunks(modeladmin, request, queryset):
    """
    Admin action to rebuild the RAG knowledge base from the Django Admin changelist.
    Enables zero-shell index rebuilding in production (Render).
    """
    try:
        call_command("build_chatbot_index")
        total = KnowledgeChunk.objects.count()
        messages.success(
            request,
            f"Successfully rebuilt knowledge base index! {total} total chunks indexed into pgvector.",
        )
    except Exception as exc:
        messages.error(request, f"Failed to rebuild knowledge base: {exc}")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("title", "source_type", "source_id", "source_url", "updated_at")
    list_filter = ("source_type", "updated_at")
    search_fields = ("title", "content", "source_url")
    actions = [rebuild_knowledge_chunks]
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("user__email", "user__username", "content")
    readonly_fields = ("created_at",)

    def short_content(self, obj):
        return obj.content[:80] + ("..." if len(obj.content) > 80 else "")
    short_content.short_description = "Content"
