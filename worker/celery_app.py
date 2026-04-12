from shared.celery_app import celery_app

# register tasks
from worker import tasks