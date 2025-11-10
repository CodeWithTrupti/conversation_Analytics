from celery import shared_task
from django.utils import timezone
from .models import Conversation
from .services import ConversationAnalyzer
import logging

logger = logging.getLogger(__name__)

@shared_task(name='analytics.tasks.analyze_single_conversation')
def analyze_single_conversation(conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        if conversation.messages.count() == 0:
            return {'status':'skipped','conversation_id':conversation_id,'reason':'No messages'}
        analyzer = ConversationAnalyzer(conversation)
        analysis = analyzer.analyze()
        return {'status':'success','conversation_id':conversation_id,'overall_score':analysis.overall_score}
    except Conversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found")
        return {'status':'error','conversation_id':conversation_id,'error':'Conversation not found'}
    except Exception as e:
        logger.error(f"Error analyzing conversation {conversation_id}: {str(e)}")
        return {'status':'error','conversation_id':conversation_id,'error':str(e)}

@shared_task(name='analytics.tasks.analyze_pending_conversations')
def analyze_pending_conversations():
    logger.info(f"Starting batch analysis at {timezone.now()}")
    pending = Conversation.objects.filter(status='pending').exclude(messages__isnull=True)
    results = {'total': pending.count(),'success':0,'errors':0,'skipped':0,'timestamp':str(timezone.now())}
    for conversation in pending:
        res = analyze_single_conversation(conversation.id)
        if res['status']=='success':
            results['success'] +=1
        elif res['status']=='error':
            results['errors'] +=1
        else:
            results['skipped'] +=1
    logger.info(f"Batch analysis complete: {results['success']} successful, {results['errors']} errors, {results['skipped']} skipped")
    return results

@shared_task(name='analytics.tasks.generate_daily_report')
def generate_daily_report():
    from django.db.models import Avg
    from .models import ConversationAnalysis
    today = timezone.now().date()
    analyses_today = ConversationAnalysis.objects.filter(created_at__date=today)
    report = {
        'date': str(today),
        'total_analyzed': analyses_today.count(),
        'avg_score': analyses_today.aggregate(Avg('overall_score'))['overall_score__avg'],
        'sentiment_distribution': {
            'positive': analyses_today.filter(sentiment='positive').count(),
            'neutral': analyses_today.filter(sentiment='neutral').count(),
            'negative': analyses_today.filter(sentiment='negative').count(),
        },
        'escalations': analyses_today.filter(escalation_needed=True).count(),
        'resolutions': analyses_today.filter(resolution=True).count(),
    }
    logger.info(f"Daily report generated: {report}")
    return report
