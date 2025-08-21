"""
Celery configuration module.
"""
from app.core.config import settings

# Broker settings
broker_url = settings.celery_broker_url
result_backend = settings.celery_result_backend

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

# Task routing
task_routes = {
    'app.tasks.style_training_tasks.*': {'queue': 'style_training'},
}

# Queue settings
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'

# Result backend settings
result_expires = 3600  # 1 hour

# Beat schedule for periodic tasks
beat_schedule = {
    'process-pending-style-posts': {
        'task': 'app.tasks.style_training_tasks.process_pending_style_posts',
        'schedule': 300.0,  # Every 5 minutes
    },
}

# Task execution settings
task_always_eager = False  # Set to True for testing
task_eager_propagates = True

# Import tasks
imports = [
    'app.tasks.style_training_tasks',
]
