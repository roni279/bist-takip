import os
import django

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bist_project.settings')
django.setup()

# Veri çekme görevini çalıştır
from hisse_takip.data_service import fetch_and_save_bist_data
from django.conf import settings

print(f"API Anahtarı: {settings.COLLECT_API_KEY}")
print("BIST verilerini çekme işlemi başlatılıyor...")

count, total = fetch_and_save_bist_data(settings.COLLECT_API_KEY)
print(f"İşlem tamamlandı: {count}/{total} hisse senedi verisi işlendi.") 