from celery import Celery
from config import get_celery_cred


celery_cred = get_celery_cred()

celery_app = Celery(
    "worker",
    broker=celery_cred.CELERY_BROKER_URL,
    backend=celery_cred.CELERY_RESULT_BACKEND,
    include=["app.celery.tasks"]
)


