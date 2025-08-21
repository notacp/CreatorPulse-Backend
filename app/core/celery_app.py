"""
Celery application configuration for background job processing.
"""
import os
from celery import Celery
from app.core.config import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('CELERY_CONFIG_MODULE', 'app.core.celery_config')

# Create the Celery application
celery_app = Celery(
    'creatorpulse',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        'app.tasks.style_training_tasks',
        'app.tasks.content_generation_tasks',
        'app.tasks.email_delivery_tasks'
    ]
)

# Configure Celery
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task execution
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    
    # Result backend
    result_expires=3600,  # 1 hour
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        'app.tasks.style_training_tasks.*': {'queue': 'style_training'},
        'app.tasks.content_generation_tasks.*': {'queue': 'content_generation'},
        'app.tasks.email_delivery_tasks.*': {'queue': 'email_delivery'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        'process-pending-style-posts': {
            'task': 'app.tasks.style_training_tasks.process_pending_style_posts',
            'schedule': 300.0,  # Every 5 minutes
        },
        'daily-content-pipelines': {
            'task': 'app.tasks.content_generation_tasks.run_daily_pipelines',
            'schedule': 86400.0,  # Every 24 hours (daily)
            'options': {'queue': 'content_generation'}
        },
        'weekly-content-cleanup': {
            'task': 'app.tasks.content_generation_tasks.cleanup_old_content',
            'schedule': 604800.0,  # Every 7 days (weekly)
            'options': {'queue': 'content_generation'}
        },
        'send-daily-emails': {
            'task': 'app.tasks.email_delivery_tasks.send_daily_emails_batch',
            'schedule': 3600.0,  # Every hour
            'options': {'queue': 'email_delivery'}
        },
        'retry-failed-emails': {
            'task': 'app.tasks.email_delivery_tasks.retry_failed_emails',
            'schedule': 21600.0,  # Every 6 hours
            'options': {'queue': 'email_delivery'}
        },
    },
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks()

if __name__ == '__main__':
    celery_app.start()
