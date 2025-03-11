from celery import shared_task
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task(name="fetch_bist_data_task")
def fetch_bist_data_task():
    """
    BIST verilerini çeken ve veritabanına kaydeden Celery görevi
    """
    # Ortam değişkenini manuel olarak da kontrol et
    API_KEY = os.environ.get('COLLECT_API_KEY') or getattr(settings, 'COLLECT_API_KEY', None)
    
    logger.info(f"Celery görevi çalışıyor: BIST verileri çekiliyor... API Anahtarı mevcut mu: {API_KEY is not None}")
    
    if not API_KEY:
        logger.error("API anahtarı bulunamadı! Görev başarısız.")
        return "API anahtarı bulunamadı"
    
    # Dinamik olarak verileri çek - bu şekilde circular import sorununu da çözüyoruz
    from .data_service import fetch_and_save_bist_data
    successful_count, total_count = fetch_and_save_bist_data(API_KEY)
    
    logger.info(f"Celery görevi tamamlandı: {successful_count}/{total_count} hisse verisi işlendi")
    return f"{successful_count}/{total_count} hisse işlendi"