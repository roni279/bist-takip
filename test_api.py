import os
import django

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bist_project.settings')
django.setup()

# API istemcisini import et
from hisse_takip.api_client import CollectAPIClient

# CollectAPI istemcisini oluştur
client = CollectAPIClient()

# BIST verilerini çek
data = client.get_bist_data()

# Sonuçları kontrol et
if data and 'result' in data:
    print(f"API başarıyla çalıştı! {len(data['result'])} hisse verisi alındı.")
    # İlk 3 hisseyi göster
    for stock in data['result'][:3]:
        print(f"{stock.get('code', 'N/A')} - {stock.get('price', 'N/A')} TL - %{stock.get('rate', 'N/A')}")
else:
    print("API çağrısı başarısız oldu veya veri döndürmedi.")
    print("Dönen veri:", data) 