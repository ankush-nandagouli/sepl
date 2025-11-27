from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sepl_project.settings')
app = Celery('sepl_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
