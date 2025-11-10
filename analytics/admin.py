from django.contrib import admin
from django.utils.html import format_html
from .models import Conversation, Message, ConversationAnalysis

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('sender', 'text', 'sequence_number', 'timestamp')
    readonly_fields = ('timestamp', 'sequence_number')
    ordering = ('sequence_number',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'message_count', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'messages__text')
    readonly_fields = ('created_at', 'updated_at', 'message_count')
    inlines = [MessageInline]
    fieldsets = (
        ('Basic Information', {'fields': ('title','status')}),
        ('Metadata', {'fields':('created_at','updated_at','message_count')}),
    )
    actions = ['trigger_analysis','mark_as_pending']
    def trigger_analysis(self, request, queryset):
        from .services import ConversationAnalyzer
        success = 0
        for conv in queryset:
            try:
                if conv.messages.count()>0:
                    ConversationAnalyzer(conv).analyze()
                    success +=1
            except Exception:
                pass
        self.message_user(request, f"Successfully analyzed {success} conversations")
    trigger_analysis.short_description="Analyze selected conversations"
    def mark_as_pending(self, request, queryset):
        count = queryset.update(status='pending')
        self.message_user(request, f"Marked {count} conversations as pending")
    mark_as_pending.short_description="Mark as pending analysis"

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id','conversation','sender','text_preview','timestamp')
    list_filter = ('sender','timestamp')
    search_fields = ('text','conversation__title')
    readonly_fields = ('timestamp','sequence_number')
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text)>100 else obj.text
    text_preview.short_description='Message'

@admin.register(ConversationAnalysis)
class ConversationAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        'id','conversation_link','overall_score_display',
        'sentiment','resolution','escalation_needed','created_at'
    )
    list_filter = ('sentiment','resolution','escalation_needed','created_at')
    search_fields = ('conversation__title','analysis_notes')
    readonly_fields = ('created_at','updated_at','quality_average','needs_attention')
    fieldsets = (
        ('Conversation', {'fields':('conversation',)}),
        ('Quality Metrics', {'fields':('clarity_score','relevance_score','accuracy_score','completeness_score','quality_average')}),
        ('Interaction Metrics', {'fields':('sentiment','empathy_score','avg_response_time')}),
        ('Resolution Metrics', {'fields':('resolution','escalation_needed','needs_attention')}),
        ('AI Performance', {'fields':('fallback_count','coherence_score','professionalism_score')}),
        ('Overall', {'fields':('overall_score','analysis_notes')}),
        ('Metadata', {'fields':('created_at','updated_at')}),
    )
    def conversation_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:analytics_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, obj.conversation.title)
    conversation_link.short_description='Conversation'
    def overall_score_display(self, obj):
        color = 'green' if obj.overall_score>=7 else 'orange' if obj.overall_score>=5 else 'red'
        return format_html('<span style="color: {}; font-weight:bold;">{:.2f}/10</span>', color, obj.overall_score)
    overall_score_display.short_description='Score'
