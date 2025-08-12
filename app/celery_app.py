"""
Celery configuration for background task processing
"""
from celery import Celery
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "clyrdia",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=200000,  # 200MB
    result_expires=3600,  # 1 hour
    beat_schedule={
        "cleanup-expired-cache": {
            "task": "app.tasks.cleanup_tasks.cleanup_expired_cache",
            "schedule": 3600.0,  # Every hour
        },
        "health-check": {
            "task": "app.tasks.monitoring_tasks.health_check",
            "schedule": 300.0,  # Every 5 minutes
        },
    }
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.analysis_tasks.*": {"queue": "analysis"},
    "app.tasks.fix_tasks.*": {"queue": "fixes"},
    "app.tasks.cleanup_tasks.*": {"queue": "maintenance"},
    "app.tasks.monitoring_tasks.*": {"queue": "monitoring"},
}

# Queue configuration
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "analysis": {"exchange": "analysis", "routing_key": "analysis"},
    "fixes": {"exchange": "fixes", "routing_key": "fixes"},
    "maintenance": {"exchange": "maintenance", "routing_key": "maintenance"},
    "monitoring": {"exchange": "monitoring", "routing_key": "monitoring"},
}

# Error handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing"""
    logger.info(f"Request: {self.request!r}")


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery configuration"""
    logger.info("Celery periodic tasks configured")


@celery_app.task_failure.connect
def handle_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **kw):
    """Handle task failures"""
    logger.error(
        "Task failed",
        task_id=task_id,
        task_name=sender.name,
        exception=str(exception),
        args=args,
        kwargs=kwargs
    )


@celery_app.task_success.connect
def handle_task_success(sender, result, **kwargs):
    """Handle successful task completion"""
    logger.info(
        "Task completed successfully",
        task_name=sender.name,
        result=result
    )


if __name__ == "__main__":
    celery_app.start() 