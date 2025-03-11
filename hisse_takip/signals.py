from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from django.db import transaction as db_transaction
from .models import Transaction, Position, FundShare, Fund, Portfolio

@receiver(post_save, sender=Transaction)
def update_position_on_transaction(sender, instance, created, **kwargs):
    """Bir işlem kaydedildiğinde portföy pozisyonlarını günceller"""
    
    # İşlem değişkenleri
    portfolio = instance.portfolio
    stock = instance.stock
    transaction_type = instance.transaction_type
    quantity = instance.quantity
    price = instance.price
    transaction_date = instance.date
    
    # Pozisyonu bul veya oluştur
    position, created = Position.objects.get_or_create(
        portfolio=portfolio,
        stock=stock,
        defaults={
            'quantity': Decimal('0'),
            'average_cost': Decimal('0'),
            'open_date': transaction_date.date() if hasattr(transaction_date, 'date') else transaction_date,
            'is_open': True
        }
    )
    
    # İşlem tipine göre pozisyonu güncelle
    if transaction_type == 'buy':
        # Alım işlemi
        new_total_cost = (position.quantity * position.average_cost) + (quantity * price)
        new_quantity = position.quantity + quantity
        
        if new_quantity > 0:
            # Yeni ortalama maliyet hesapla
            position.average_cost = new_total_cost / new_quantity
        
        position.quantity = new_quantity
        position.is_open = True  # Pozisyon açık
        
    elif transaction_type == 'sell':
        # Satım işlemi
        position.quantity -= quantity
        
        # Eğer tüm hisseler satıldıysa pozisyonu kapat
        if position.quantity <= 0:
            position.quantity = Decimal('0')
            position.is_open = False  # Pozisyon kapalı
            
    elif transaction_type == 'dividend':
        # Temettü işlemi - pozisyonu değiştirmez, sadece portföy değerini etkiler
        pass
        
    elif transaction_type == 'split':
        # Hisse bölünmesi - miktarı artırır, ortalama maliyeti düşürür
        split_ratio = price  # Bölünme oranı
        position.quantity *= split_ratio
        position.average_cost /= split_ratio
        
    elif transaction_type == 'merge':
        # Hisse birleşmesi - miktarı azaltır, ortalama maliyeti artırır
        merge_ratio = price  # Birleşme oranı
        position.quantity /= merge_ratio
        position.average_cost *= merge_ratio
    
    # Pozisyonu kaydet
    position.save()

@receiver(post_delete, sender=Transaction)
def update_position_on_transaction_delete(sender, instance, **kwargs):
    """Bir işlem silindiğinde, ilgili pozisyonu yeniden hesaplar"""
    
    portfolio = instance.portfolio
    stock = instance.stock
    
    try:
        # İlgili pozisyonu bul
        position = Position.objects.get(portfolio=portfolio, stock=stock)
        
        # Pozisyon için tüm işlemleri yeniden hesapla
        transactions = Transaction.objects.filter(
            portfolio=portfolio, 
            stock=stock
        ).order_by('date')
        
        if not transactions.exists():
            # Eğer başka işlem kalmadıysa pozisyonu sil
            position.delete()
            return
        
        # Pozisyonu sıfırla
        position.quantity = Decimal('0')
        position.average_cost = Decimal('0')
        position.open_date = transactions.first().date
        
        # Tüm işlemleri yeniden hesapla
        total_cost = Decimal('0')
        
        for tx in transactions:
            if tx.transaction_type == 'buy':
                # Alım işlemi
                total_cost += tx.quantity * tx.price
                position.quantity += tx.quantity
            elif tx.transaction_type == 'sell':
                # Satım işlemi
                position.quantity -= tx.quantity
            # Diğer işlem tipleri için ek mantık eklenebilir
        
        # Ortalama maliyeti hesapla
        if position.quantity > 0:
            position.average_cost = total_cost / position.quantity
            position.is_open = True
        else:
            position.is_open = False
        
        position.save()
    
    except Position.DoesNotExist:
        # Pozisyon yoksa bir şey yapma
        pass

@receiver(post_save, sender=FundShare)
def update_fund_on_share_creation(sender, instance, created, **kwargs):
    """Bir fon payı oluşturulduğunda/güncellendiğinde fon değerlerini günceller"""
    
    if created:  # Yeni bir yatırımcı eklendiğinde
        fund = instance.fund
        # Başlangıç değerini ve güncel değeri artır
        fund.initial_value += instance.initial_investment
        fund.current_value += instance.initial_investment
        # Toplam pay adedini artır
        fund.total_shares += instance.shares_count
        fund.save()
    else:
        # Pay bilgileri güncellendiğinde - fon değerleri değişmeyecektir
        # Sadece pay miktarı değişirse total_shares güncellenmeli
        # Bu kısımda daha karmaşık bir mantık gerekebilir
        pass

@receiver(post_delete, sender=FundShare)
def update_fund_on_share_deletion(sender, instance, **kwargs):
    """Bir fon payı silindiğinde fon değerlerini günceller"""
    
    fund = instance.fund
    
    # Fonun değerini ve pay adedini azalt
    if fund.total_shares > 0 and fund.total_shares >= instance.shares_count:
        # Pay değerini hesapla
        share_value = fund.current_value / fund.total_shares
        
        # Başlangıç değerini azalt (ama negatife düşmesini önle)
        fund.initial_value = max(Decimal('0'), fund.initial_value - instance.initial_investment)
        
        # Güncel değeri, silinen payların güncel değeri kadar azalt
        current_share_value = instance.shares_count * share_value
        fund.current_value = max(Decimal('0'), fund.current_value - current_share_value)
        
        # Toplam pay adedini azalt
        fund.total_shares = max(Decimal('0'), fund.total_shares - instance.shares_count)
        
        fund.save()

@receiver(post_save, sender=Portfolio)
def update_fund_on_portfolio_change(sender, instance, **kwargs):
    """Portföy değiştiğinde bağlı fonu güncelle"""
    if instance.fund:
        instance.fund.update_value_from_portfolios()

@receiver(post_save, sender=Position)
def update_fund_on_position_change(sender, instance, **kwargs):
    """Pozisyon değiştiğinde bağlı fonu güncelle"""
    portfolio = instance.portfolio
    if portfolio and portfolio.fund:
        portfolio.fund.update_value_from_portfolios()

@receiver(post_save, sender=Transaction)
def update_fund_on_transaction(sender, instance, **kwargs):
    """İşlem yapıldığında bağlı fonu güncelle"""
    portfolio = instance.portfolio
    if portfolio and portfolio.fund:
        # Direkt güncelle
        portfolio.fund.update_value_from_portfolios() 