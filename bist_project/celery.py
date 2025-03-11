import os
from celery import Celery

# Django settings modülünü tanımla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bist_project.settings')

# Celery uygulamasını oluştur
app = Celery('bist_project')

# Celery ayarlarını Django settings.py'den oku (CELERY_ ile başlayanlar)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django uygulamalarındaki task'ları otomatik keşfet
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 