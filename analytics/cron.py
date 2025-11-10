import logging
from django.utils import timezone
from .models import Conversation
from .services import ConversationAnalyzer

logger = logging.getLogger(__name__)

def run_daily_analysis():
    logger.info(f"Starting daily analysis task at {timezone.now()}")
    pending_conversations = Conversation.objects.filter(status='pending').exclude(messages__isnull=True)
    total = pending_conversations.count()
    success_count = error_count = 0
    for conversation in pending_conversations:
        try:
            if conversation.messages.count() == 0:
                logger.warning(f"Skipping conversation {conversation.id} – no messages")
                continue
            analyzer = ConversationAnalyzer(conversation)
            analyzer.analyze()
            success_count += 1
            logger.info(f"Successfully analyzed conversation {conversation.id}")
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to analyze conversation {conversation.id}: {str(e)}")
            conversation.status = 'error'
            conversation.save()
    logger.info(f"Daily analysis completed. Total: {total}, Success: {success_count}, Errors: {error_count}")
    return {'total': total, 'success': success_count, 'errors': error_count, 'timestamp': timezone.now()}
