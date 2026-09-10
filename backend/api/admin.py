from django.contrib import admin

from api.models import EntreeCacheRecommandation, JournalAppelLLM


@admin.register(EntreeCacheRecommandation)
class EntreeCacheRecommandationAdmin(admin.ModelAdmin):
    list_display = ('cle', 'utilisateur', 'expire_a', 'created_at')
    search_fields = ('cle', 'utilisateur__username')
    list_filter = ('expire_a',)


@admin.register(JournalAppelLLM)
class JournalAppelLLMAdmin(admin.ModelAdmin):
    list_display = ('status', 'cache_hit', 'duration_ms', 'created_at')
    search_fields = ('user_hash', 'prompt_hash')
    list_filter = ('status', 'cache_hit')
