import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conversation_analytics.settings')

app = Celery('conversation_analytics')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

app.conf.beat_schedule = {
    'analyze-pending-daily': {
        'task': 'analytics.tasks.analyze_pending_conversations',
        'schedule': crontab(hour=0, minute=0),
    },
    'generate-daily-report': {
        'task': 'analytics.tasks.generate_daily_report',
        'schedule': crontab(hour=1, minute=0),
    },
}

app.conf.timezone = 'UTC'
