import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max
from ...models import Stock, PriceData

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Her hisse için sadece her günün son kaydını tutar, diğer tüm kayıtları temizler'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-days',
            type=int,
            default=None,
            help='Son kaç günün TÜM verilerini koruyacağı (varsayılan: koruma yok)'
        )
        
    def handle(self, *args, **options):
        keep_days = options['keep_days']
        
        self.stdout.write("Her hisse için her günün sadece son kaydını saklayacak veri temizliği başlıyor...")
        
        # Korunacak en son veri tarihini belirle (opsiyonel)
        if keep_days:
            keep_date = timezone.now() - timedelta(days=keep_days)
            self.stdout.write(f"Son {keep_days} günün verileri tamamen korunacak ({keep_date} tarihinden yeniler)")
        else:
            keep_date = None
            
        # Her hisse için işlem yap
        stocks = Stock.objects.all()
        total_kept = 0
        total_deleted = 0
        
        for stock in stocks:
            # Günlük son kayıtları bul
            daily_last_ids = []
            
            # Verinin bulunduğu günleri al
            if keep_date:
                # Son X gün hariç günleri al
                days_with_data = PriceData.objects.filter(
                    stock=stock, 
                    timestamp__lt=keep_date
                ).dates('timestamp', 'day')
            else:
                # Tüm günleri al
                days_with_data = PriceData.objects.filter(
                    stock=stock
                ).dates('timestamp', 'day')
            
            # Her gün için son kaydı bul
            for day in days_with_data:
                day_end = day + timedelta(days=1) - timedelta(microseconds=1)
                
                # O günün son kaydını bul
                last_record_id = PriceData.objects.filter(
                    stock=stock,
                    timestamp__gte=day,
                    timestamp__lte=day_end
                ).order_by('-timestamp').values_list('id', flat=True).first()
                
                if last_record_id:
                    daily_last_ids.append(last_record_id)
                    total_kept += 1
            
            # Korunacak kayıtlar: her günün son kaydı + keep_date'den yeni tüm kayıtlar
            if keep_date:
                to_delete = PriceData.objects.filter(
                    stock=stock,
                    timestamp__lt=keep_date  # Son X gün hariç
                ).exclude(
                    id__in=daily_last_ids    # Günlük son kayıtlar hariç
                )
            else:
                to_delete = PriceData.objects.filter(
                    stock=stock
                ).exclude(
                    id__in=daily_last_ids    # Günlük son kayıtlar hariç
                )
            
            # Silme işlemi
            count = to_delete.count()
            to_delete.delete()
            total_deleted += count
            
            self.stdout.write(f"{stock.code}: {len(daily_last_ids)} günlük kayıt korundu, {count} eski kayıt silindi")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Temizlik tamamlandı: {total_kept} günlük kayıt korundu, {total_deleted} eski kayıt silindi!"
            )
        ) 