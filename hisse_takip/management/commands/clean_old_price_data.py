import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max
from ...models import Stock, PriceData

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Belirli bir süreden eski fiyat verilerini temizler, hisse başına sadece son kaydı tutar'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Kaç günden eski verilerin temizleneceği (varsayılan: 30)'
        )
        
        parser.add_argument(
            '--keep-daily',
            action='store_true',
            help='Her hisse için her gün bir kayıt tut'
        )
        
    def handle(self, *args, **options):
        days = options['days']
        keep_daily = options['keep_daily']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        self.stdout.write(f"{cutoff_date} tarihinden eski verileri temizliyorum...")
        
        # Her hisse için son kaydı bul
        stocks = Stock.objects.all()
        cleaned_count = 0
        
        for stock in stocks:
            # Her hisse için en son kaydı her zaman tut
            latest_record = PriceData.objects.filter(stock=stock).latest('timestamp')
            
            # Silinecek kayıtları belirle
            if keep_daily:
                # Her gün için sadece bir kayıt tut
                # Önce her günün son kaydını bulalım
                days_with_data = PriceData.objects.filter(
                    stock=stock,
                    timestamp__lt=cutoff_date
                ).dates('timestamp', 'day')
                
                preserved_ids = []
                for day in days_with_data:
                    # Her gün için son kaydın ID'sini al
                    day_end = day + timedelta(days=1) - timedelta(microseconds=1)
                    last_record_id = PriceData.objects.filter(
                        stock=stock,
                        timestamp__gte=day,
                        timestamp__lte=day_end
                    ).order_by('-timestamp').values_list('id', flat=True).first()
                    
                    if last_record_id:
                        preserved_ids.append(last_record_id)
                
                # Son kayıtları ve korunacak günlük kayıtları hariç tut
                to_delete = PriceData.objects.filter(
                    stock=stock,
                    timestamp__lt=cutoff_date
                ).exclude(
                    id__in=preserved_ids
                ).exclude(
                    id=latest_record.id
                )
            else:
                # Sadece en son kaydı tut, diğerlerini sil
                to_delete = PriceData.objects.filter(
                    stock=stock,
                    timestamp__lt=cutoff_date
                ).exclude(id=latest_record.id)
            
            count = to_delete.count()
            to_delete.delete()
            cleaned_count += count
            
            self.stdout.write(f"{stock.code} için {count} eski kayıt temizlendi")
        
        self.stdout.write(
            self.style.SUCCESS(f"Toplam {cleaned_count} eski fiyat verisi temizlendi!")
        ) 