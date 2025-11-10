from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Conversation(models.Model):
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Analysis'),
            ('analyzed', 'Analyzed'),
            ('error', 'Analysis Error')
        ],
        default='pending'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Conversations'
    
    def __str__(self):
        return f"{self.title or f'Conversation {self.id}'} - {self.created_at.strftime('%Y-%m-%d')}"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def user_message_count(self):
        return self.messages.filter(sender='user').count()
    
    @property
    def ai_message_count(self):
        return self.messages.filter(sender='ai').count()

class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(
        max_length=20,
        choices=[('user', 'User'), ('ai', 'AI')]
    )
    text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    sequence_number = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sequence_number', 'timestamp']
    
    def __str__(self):
        return f"{self.sender}: {self.text[:50]}..."
    
    def save(self, *args, **kwargs):
        if not self.sequence_number:
            last_msg = Message.objects.filter(
                conversation=self.conversation
            ).order_by('-sequence_number').first()
            self.sequence_number = (last_msg.sequence_number + 1) if last_msg else 1
        super().save(*args, **kwargs)

class ConversationAnalysis(models.Model):
    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.CASCADE,
        related_name='analysis'
    )
    clarity_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    relevance_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    accuracy_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    completeness_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    sentiment = models.CharField(max_length=20, choices=[('positive','Positive'),('neutral','Neutral'),('negative','Negative'),('mixed','Mixed')])
    empathy_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    avg_response_time = models.FloatField(help_text="Average response time in seconds")
    resolution = models.BooleanField(default=False)
    escalation_needed = models.BooleanField(default=False)
    fallback_count = models.IntegerField(default=0)
    coherence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    professionalism_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    overall_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(10.0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analysis_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Conversation Analyses'
    
    def __str__(self):
        return f"Analysis for {self.conversation} - Score: {self.overall_score:.2f}/10"
    
    @property
    def quality_average(self):
        return (self.clarity_score + self.relevance_score + self.accuracy_score + self.completeness_score) / 4
    
    @property
    def needs_attention(self):
        return self.overall_score < 5.0 or self.escalation_needed
