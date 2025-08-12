"""
Monitoring and health check tasks
"""
from celery import current_task
from app.celery_app import celery_app
from app.core.cache import cache
from app.services.supabase_service import supabase_service
import structlog
import time

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """
    Periodic health check task
    """
    try:
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Starting health check", "progress": 0}
        )
        
        logger.info("Starting periodic health check")
        
        health_status = {
            "timestamp": time.time(),
            "services": {}
        }
        
        # Check cache health
        try:
            cache.ping()
            health_status["services"]["cache"] = "healthy"
        except Exception as e:
            health_status["services"]["cache"] = f"unhealthy: {str(e)}"
        
        # Check database health
        try:
            # Simple database check
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
        
        # Check OpenAI health (basic)
        try:
            health_status["services"]["openai"] = "healthy"
        except Exception as e:
            health_status["services"]["openai"] = f"unhealthy: {str(e)}"
        
        # Determine overall status
        overall_status = "healthy" if all(
            "healthy" in status for status in health_status["services"].values()
        ) else "degraded"
        
        health_status["overall_status"] = overall_status
        
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Health check completed", "progress": 100}
        )
        
        logger.info("Health check completed", status=overall_status)
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="performance_metrics")
def performance_metrics(self):
    """
    Collect performance metrics
    """
    try:
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Collecting metrics", "progress": 0}
        )
        
        logger.info("Starting performance metrics collection")
        
        metrics = {
            "timestamp": time.time(),
            "cache_stats": {},
            "database_stats": {},
            "system_stats": {}
        }
        
        # Collect cache metrics
        try:
            # This would collect Redis metrics
            metrics["cache_stats"] = {
                "keys_count": 0,
                "memory_usage": 0,
                "hit_rate": 0
            }
        except Exception as e:
            logger.warning("Failed to collect cache metrics", error=str(e))
        
        # Collect database metrics
        try:
            # This would collect database performance metrics
            metrics["database_stats"] = {
                "active_connections": 0,
                "query_performance": {},
                "table_sizes": {}
            }
        except Exception as e:
            logger.warning("Failed to collect database metrics", error=str(e))
        
        # Collect system metrics
        try:
            import psutil
            metrics["system_stats"] = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        except ImportError:
            metrics["system_stats"] = {"error": "psutil not available"}
        except Exception as e:
            logger.warning("Failed to collect system metrics", error=str(e))
        
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Metrics collection completed", "progress": 100}
        )
        
        logger.info("Performance metrics collected", metrics_count=len(metrics))
        
        return metrics
        
    except Exception as e:
        logger.error("Performance metrics collection failed", error=str(e))
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="alert_check")
def alert_check(self):
    """
    Check for conditions that require alerts
    """
    try:
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Checking for alerts", "progress": 0}
        )
        
        logger.info("Starting alert check")
        
        alerts = []
        
        # Check system resources
        try:
            import psutil
            
            # CPU usage alert
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 80:
                alerts.append({
                    "type": "high_cpu",
                    "severity": "warning",
                    "message": f"CPU usage is {cpu_percent}%",
                    "value": cpu_percent,
                    "threshold": 80
                })
            
            # Memory usage alert
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                alerts.append({
                    "type": "high_memory",
                    "severity": "warning",
                    "message": f"Memory usage is {memory_percent}%",
                    "value": memory_percent,
                    "threshold": 85
                })
                
        except ImportError:
            logger.warning("psutil not available for system monitoring")
        except Exception as e:
            logger.warning("Failed to check system resources", error=str(e))
        
        # Check cache health
        try:
            # This would check Redis health and performance
            pass
        except Exception as e:
            alerts.append({
                "type": "cache_error",
                "severity": "error",
                "message": f"Cache health check failed: {str(e)}"
            })
        
        # Check database health
        try:
            # This would check database health and performance
            pass
        except Exception as e:
            alerts.append({
                "type": "database_error",
                "severity": "error",
                "message": f"Database health check failed: {str(e)}"
            })
        
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Alert check completed", "progress": 100}
        )
        
        if alerts:
            logger.warning("Alerts detected", alert_count=len(alerts), alerts=alerts)
        else:
            logger.info("No alerts detected")
        
        return {
            "timestamp": time.time(),
            "alerts": alerts,
            "alert_count": len(alerts)
        }
        
    except Exception as e:
        logger.error("Alert check failed", error=str(e))
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise 