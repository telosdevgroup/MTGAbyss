import os
from celery import Celery

# Monkey patch Celery's solo pool to prevent NotImplementedError traceback on Windows Ctrl+C shutdown
try:
    from celery.concurrency.solo import TaskPool
    TaskPool.terminate_job = lambda self, *args, **kwargs: None
except Exception:
    pass

# Use MongoDB as the message broker and backend
# Point to the Beast MongoDB server
MONGO_URL = os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017")

# Celery MongoDB broker requires a database name suffix
broker_url = f"{MONGO_URL}/celery_broker"
result_backend = f"{MONGO_URL}/celery_results"

app = Celery(
    "mtgabyss",
    broker=broker_url,
    backend=result_backend,
    include=["tasks"]
)

# Silence verbose task received/succeeded logs to keep console clean
from celery.signals import setup_logging
import logging

@setup_logging.connect
def config_loggers(*args, **kwargs):
    # Quiet the internal Celery loggers to WARNING level
    logging.getLogger('celery').setLevel(logging.WARNING)
    logging.getLogger('celery.task').setLevel(logging.WARNING)

app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Task routing configuration
    task_routes={
        "tasks.process_art_vl": {"queue": "vl"},
        "tasks.generate_embedding": {"queue": "gpu-tasks"},
        "tasks.generate_lure": {"queue": "ai-lures"},
        "tasks.precompute_similar_cards": {"queue": "builder-tasks"},
        "tasks.generate_card_page": {"queue": "builder-tasks"},
        "tasks.deploy_card_page": {"queue": "builder-tasks"},
        "tasks.generate_and_deploy_page": {"queue": "builder-tasks"},
    }
)

if __name__ == "__main__":
    app.start()
