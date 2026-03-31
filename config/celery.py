# oilbank_ecommerce/celery.py

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create the Celery application
app = Celery("oilbank_ecommerce")

# Load task modules from all registered Django app configs using CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in installed apps
app.autodiscover_tasks()


# Debug task for testing purposes
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
