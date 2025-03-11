import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from ...data_service import fetch_and_save_bist_data

# Loglama ayarları
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'CollectAPI\'den BIST verilerini çeker ve veritabanına kaydeder'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--api-key',
            type=str,
            help='Kullanılacak API anahtarı (belirtilmezse settings.py\'deki veya çevre değişkeni kullanılır)'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"BIST verileri çekiliyor... ({start_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        api_key = options.get('api_key')
        successful_count, total_count = fetch_and_save_bist_data(api_key)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"İşlem tamamlandı! {successful_count}/{total_count} hisse kaydedildi. "
                f"Süre: {duration:.2f} saniye"
            )
        ) 