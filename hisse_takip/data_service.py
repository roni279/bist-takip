import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from .models import Stock, PriceData
from .api_client import CollectAPIClient
import decimal

# Loglama ayarları
logger = logging.getLogger(__name__)

def fetch_and_save_bist_data(api_key=None):
    """
    CollectAPI'den BIST verilerini çeker ve veritabanına kaydeder.
    
    Args:
        api_key (str, optional): API anahtarı. None ise varsayılan anahtar kullanılır.
        
    Returns:
        tuple: (başarılı_kayıt_sayısı, toplam_hisse_sayısı)
    """
    # API anahtarını ayarlardan al
    if api_key is None:
        api_key = getattr(settings, 'COLLECT_API_KEY', None)
        
    if api_key is None:
        logger.error("API anahtarı bulunamadı, veri çekilemeyecek")
        return 0, 0
        
    client = CollectAPIClient(api_key)
    data = client.get_bist_data()
    
    if not data or 'result' not in data:
        logger.error("API'den veri alınamadı veya veri formatı beklendiği gibi değil")
        return 0, 0
    
    stocks_data = data['result']
    successful_count = 0
    total_count = len(stocks_data)
    skipped_count = 0
    
    logger.info(f"Toplam {total_count} hisse verisi işlenecek")
    
    # Tüm kayıtlar için tek bir transaction kullan
    with transaction.atomic():
        for stock_data in stocks_data:
            try:
                # Gerekli alanları kontrol et
                if not all(key in stock_data for key in ['code', 'text', 'lastprice', 'rate']):
                    logger.warning(f"Eksik veri: {stock_data}")
                    continue
                
                # Stock kaydını bul veya oluştur
                stock, created = Stock.objects.update_or_create(
                    code=stock_data['code'],
                    defaults={
                        'name': stock_data.get('text', ''),
                        'icon': stock_data.get('icon', '')
                    }
                )
                
                if created:
                    logger.info(f"Yeni hisse eklendi: {stock.code}")
                
                # Decimal dönüşümlerini güvenli bir şekilde yap
                try:
                    price = Decimal(str(stock_data.get('lastprice', 0)))
                    change_percentage = Decimal(str(stock_data.get('rate', 0)))
                    volume = Decimal(str(stock_data.get('hacim', 0))) if 'hacim' in stock_data else None
                    
                    # None değerlerini kontrol et
                    min_price = Decimal(str(stock_data.get('min', 0))) if 'min' in stock_data and stock_data['min'] is not None else None
                    max_price = Decimal(str(stock_data.get('max', 0))) if 'max' in stock_data and stock_data['max'] is not None else None
                    update_time = stock_data.get('time', '')
                except (ValueError, TypeError, decimal.InvalidOperation) as e:
                    logger.error(f"Sayısal değer dönüştürme hatası: {e}, Veri: {stock_data}")
                    continue
                
                # Aynı hisse için son kaydı kontrol et
                latest_price_data = PriceData.objects.filter(
                    stock=stock, 
                    update_time=update_time
                ).order_by('-timestamp').first()
                
                # Eğer aynı güncelleme saatine sahip bir kayıt varsa ve veriler aynıysa, yeni kayıt ekleme
                if latest_price_data and \
                   latest_price_data.price == price and \
                   latest_price_data.change_percentage == change_percentage:
                    logger.debug(f"Tekrarlanan veri atlandı: {stock.code} - {update_time}")
                    skipped_count += 1
                    continue
                
                # Yeni bir fiyat verisi oluştur
                PriceData.objects.create(
                    stock=stock,
                    price=price,
                    change_percentage=change_percentage,
                    volume=volume,
                    min_price=min_price,
                    max_price=max_price,
                    update_time=update_time
                )
                
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Hisse verisi kaydedilirken hata: {e}, Veri: {stock_data}")
    
    logger.info(f"{successful_count}/{total_count} hisse verisi başarıyla kaydedildi, {skipped_count} tekrarlanan veri atlandı")
    return successful_count, total_count 