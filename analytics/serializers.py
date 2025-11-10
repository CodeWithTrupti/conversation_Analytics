from rest_framework import serializers
from .models import Conversation, Message, ConversationAnalysis
from django.utils import timezone

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender', 'text', 'timestamp', 'sequence_number']
        read_only_fields = ['id', 'timestamp', 'sequence_number']

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'status', 'messages', 'message_count']
        read_only_fields = ['id', 'created_at', 'updated_at', 'status']

class ConversationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    messages = serializers.ListField(child=serializers.DictField(), min_length=1)
    
    def validate_messages(self, value):
        for idx, msg in enumerate(value):
            if 'sender' not in msg or 'message' not in msg:
                raise serializers.ValidationError(f"Message at index {idx} must contain 'sender' and 'message'")
            if msg['sender'] not in ['user', 'ai']:
                raise serializers.ValidationError(f"Message at index {idx}: sender must be 'user' or 'ai', got '{msg['sender']}'")
            if not isinstance(msg['message'], str) or not msg['message'].strip():
                raise serializers.ValidationError(f"Message at index {idx}: 'message' must be a non-empty string")
        return value
    
    def create(self, validated_data):
        messages_data = validated_data.pop('messages')
        title = validated_data.get('title', f"Conversation {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        conversation = Conversation.objects.create(title=title)
        for idx, msg_data in enumerate(messages_data, start=1):
            Message.objects.create(
                conversation=conversation,
                sender=msg_data['sender'],
                text=msg_data['message'],
                sequence_number=idx
            )
        return conversation

class ConversationAnalysisSerializer(serializers.ModelSerializer):
    conversation_title = serializers.CharField(source='conversation.title', read_only=True)
    conversation_id = serializers.IntegerField(source='conversation.id', read_only=True)
    quality_average = serializers.FloatField(read_only=True)
    needs_attention = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ConversationAnalysis
        fields = [
            'id', 'conversation_id', 'conversation_title',
            'clarity_score', 'relevance_score', 'accuracy_score', 'completeness_score',
            'sentiment', 'empathy_score', 'avg_response_time',
            'resolution', 'escalation_needed',
            'fallback_count', 'coherence_score', 'professionalism_score',
            'overall_score', 'quality_average', 'needs_attention',
            'created_at', 'updated_at', 'analysis_notes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AnalysisReportSerializer(serializers.Serializer):
    conversation = ConversationSerializer(read_only=True)
    analysis = ConversationAnalysisSerializer(read_only=True)
    insights = serializers.DictField(read_only=True)
