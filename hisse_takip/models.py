from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.db import connection
from decimal import Decimal

# Stock modeli - temel hisse senedi bilgileri
class Stock(models.Model):
    code = models.CharField(max_length=10, primary_key=True, verbose_name="Hisse Kodu")
    name = models.CharField(max_length=100, verbose_name="Şirket Adı")
    icon = models.URLField(max_length=255, blank=True, null=True, verbose_name="Hisse İkonu URL")
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        verbose_name = "Hisse Senedi"
        verbose_name_plural = "Hisse Senetleri"
        ordering = ['code']

# PriceData modeli - hisse senedi fiyat verileri
class PriceData(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='prices', verbose_name="Hisse")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat")
    change_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Değişim (%)")
    volume = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True, verbose_name="İşlem Hacmi")
    min_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Günlük En Düşük")
    max_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Günlük En Yüksek")
    update_time = models.CharField(max_length=10, blank=True, null=True, verbose_name="Güncelleme Saati")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Kayıt Zamanı")
    
    def __str__(self):
        return f"{self.stock.code} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        verbose_name = "Fiyat Verisi"
        verbose_name_plural = "Fiyat Verileri"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['stock', 'timestamp']),
        ]
    
    @property
    def is_positive(self):
        """Fiyat değişimi pozitif mi?"""
        return self.change_percentage >= 0

# Portföy modeli - kullanıcının oluşturduğu yatırım portföyü
class Portfolio(models.Model):
    RISK_CHOICES = [
        ('low', 'Düşük Risk'),
        ('medium', 'Orta Risk'),
        ('high', 'Yüksek Risk'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Portföy Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    investor = models.ForeignKey('Investor', on_delete=models.SET_NULL, verbose_name="Yatırımcı", 
                                 null=True, blank=True, related_name="portfolios")
    fund = models.ForeignKey('Fund', on_delete=models.SET_NULL, verbose_name="Bağlı Fon",
                           null=True, blank=True, related_name="portfolios")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    currency = models.CharField(max_length=3, default="TRY", verbose_name="Para Birimi")
    target_return = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, verbose_name="Hedef Getiri (%)")
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default='medium', verbose_name="Risk Seviyesi")
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    class Meta:
        verbose_name = "Portföy"
        verbose_name_plural = "Portföyler"
        ordering = ['-created_at']
    
    @property
    def total_current_value(self):
        """Portföyün güncel toplam değerini hesaplar"""
        return sum(position.current_value for position in self.positions.all())
    
    @property
    def total_cost(self):
        """Portföyün toplam maliyetini hesaplar"""
        return sum(position.total_cost for position in self.positions.all())
    
    @property
    def total_profit_loss(self):
        """Portföyün toplam kar/zararını hesaplar"""
        return self.total_current_value - self.total_cost
    
    @property
    def profit_loss_percentage(self):
        """Portföyün kar/zarar yüzdesini hesaplar"""
        if self.total_cost == 0:
            return 0
        return (self.total_profit_loss / self.total_cost) * 100

    def update_fund_value(self):
        """Bağlı fonun değerini günceller"""
        if self.fund:
            # Fonun değerini güncelle
            self.fund.update_value_from_portfolios()
            return True
        return False

# Pozisyon modeli - portföydeki hisse senedi pozisyonu
class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='positions', verbose_name="Portföy")
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name='positions', verbose_name="Hisse Senedi")
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Miktar")
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ortalama Maliyet")
    open_date = models.DateField(verbose_name="Açılış Tarihi")
    notes = models.TextField(blank=True, null=True, verbose_name="Notlar")
    is_open = models.BooleanField(default=True, verbose_name="Açık Pozisyon mu?")
    target_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Hedef Fiyat")
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Zarar Kesme")
    
    def __str__(self):
        return f"{self.stock.code} - {self.quantity} adet"
    
    class Meta:
        verbose_name = "Pozisyon"
        verbose_name_plural = "Pozisyonlar"
        ordering = ['portfolio', 'stock__code']
        unique_together = ['portfolio', 'stock']  # Bir portföyde her hisse için tek pozisyon
    
    @property
    def total_cost(self):
        """Pozisyonun toplam maliyetini hesaplar"""
        return self.quantity * self.average_cost
    
    @property
    def current_price(self):
        """Hissenin güncel fiyatını döndürür"""
        latest_price = self.stock.prices.order_by('-timestamp').first()
        if latest_price:
            return latest_price.price
        return 0
    
    @property
    def current_value(self):
        """Pozisyonun güncel değerini hesaplar"""
        return self.quantity * self.current_price
    
    @property
    def profit_loss(self):
        """Pozisyonun kar/zararını hesaplar"""
        return self.current_value - self.total_cost
    
    @property
    def profit_loss_percentage(self):
        """Pozisyonun kar/zarar yüzdesini hesaplar"""
        if self.total_cost == 0:
            return 0
        return (self.profit_loss / self.total_cost) * 100

# İşlem modeli - alım/satım işlemleri
class Transaction(models.Model):
    """Hisse alım-satım işlemlerini tutan model"""
    TRANSACTION_TYPES = [
        ('buy', 'Alım'),
        ('sell', 'Satım'),
        ('dividend', 'Temettü'),
        ('split', 'Bölünme'),
        ('merger', 'Birleşme'),
        ('rights', 'Bedelsiz/Rüçhan'),
    ]
    
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='transactions', verbose_name="Portföy")
    investor = models.ForeignKey('Investor', on_delete=models.SET_NULL, related_name='transactions', 
                               null=True, blank=True, verbose_name="Yatırımcı")
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name='transactions', verbose_name="Hisse Senedi")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name="İşlem Tipi")
    date = models.DateTimeField(verbose_name="İşlem Tarihi")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat")
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Miktar")
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Komisyon")
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Vergi")
    notes = models.TextField(blank=True, null=True, verbose_name="Notlar")
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.stock.code} - {self.quantity} adet"
    
    class Meta:
        verbose_name = "İşlem"
        verbose_name_plural = "İşlemler"
        ordering = ['-date']
    
    @property
    def total_amount(self):
        """İşlemin toplam tutarını hesaplar (komisyon ve vergi dahil)"""
        amount = self.price * self.quantity
        if self.transaction_type == 'buy':
            return amount + self.commission + self.tax
        else:  # sell
            return amount - self.commission - self.tax

    def save(self, *args, **kwargs):
        # Eğer investor değeri belirtilmemişse, portföyün investor değerini al
        if not self.investor and self.portfolio and self.portfolio.investor:
            self.investor = self.portfolio.investor
            
        # İşlemi kaydet
        super().save(*args, **kwargs)
        
        # Yatırımcının toplam yatırım tutarını güncelle
        if self.investor:
            self.investor.update_investment_total()

# İzleme Listesi
class WatchList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists', verbose_name="Kullanıcı")
    name = models.CharField(max_length=100, verbose_name="Liste Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    class Meta:
        verbose_name = "İzleme Listesi"
        verbose_name_plural = "İzleme Listeleri"
        ordering = ['user', 'name']

# İzleme Listesi Öğesi
class WatchListItem(models.Model):
    watchlist = models.ForeignKey(WatchList, on_delete=models.CASCADE, related_name='items', verbose_name="İzleme Listesi")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='watchlist_items', verbose_name="Hisse Senedi")
    target_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Hedef Fiyat")
    notes = models.TextField(blank=True, null=True, verbose_name="Notlar")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Eklenme Tarihi")
    
    def __str__(self):
        return f"{self.stock.code} - {self.watchlist.name}"
    
    class Meta:
        verbose_name = "İzleme Öğesi"
        verbose_name_plural = "İzleme Öğeleri"
        ordering = ['watchlist', 'stock__code']
        unique_together = ['watchlist', 'stock']  # Bir listede her hisse bir kez olabilir

# Fiyat Alarmı
class Alert(models.Model):
    CONDITION_TYPES = [
        ('above', 'Üzerinde'),
        ('below', 'Altında'),
        ('percent_change', 'Yüzde Değişim'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts', verbose_name="Kullanıcı")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='alerts', verbose_name="Hisse Senedi")
    condition_type = models.CharField(max_length=15, choices=CONDITION_TYPES, verbose_name="Koşul Tipi")
    threshold_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Eşik Değeri")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    triggered_at = models.DateTimeField(blank=True, null=True, verbose_name="Tetiklenme Tarihi")
    notification_sent = models.BooleanField(default=False, verbose_name="Bildirim Gönderildi mi?")
    
    def __str__(self):
        condition = self.get_condition_type_display()
        return f"{self.stock.code} {condition} {self.threshold_value}"
    
    class Meta:
        verbose_name = "Alarm"
        verbose_name_plural = "Alarmlar"
        ordering = ['user', 'stock__code', '-created_at']

# Portföy Anlık Görüntüsü - tarihe göre portföy değerini saklar
class PortfolioSnapshot(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='snapshots', verbose_name="Portföy")
    date = models.DateField(verbose_name="Tarih")
    total_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Toplam Değer")
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Toplam Maliyet")
    profit_loss = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Kar/Zarar")
    profit_loss_percentage = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Kar/Zarar Yüzdesi")
    benchmark_comparison = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Kıyaslama Farkı")
    
    def __str__(self):
        return f"{self.portfolio.name} - {self.date}"
    
    class Meta:
        verbose_name = "Portföy Anlık Görüntüsü"
        verbose_name_plural = "Portföy Anlık Görüntüleri"
        ordering = ['portfolio', '-date']
        unique_together = ['portfolio', 'date']  # Her portföy için günde bir görüntü 

class Investor(models.Model):
    """Yatırımcı bilgilerini tutan model"""
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL,  # User silinirse Investor null olur
        related_name='investor',     # User'dan erişim: user.investor
        null=True,                   # Tüm Investor kayıtları için User gerekli değil
        blank=True,                  # Admin formunda zorunlu değil
        verbose_name="Kullanıcı Hesabı"
    )
    name = models.CharField(max_length=100, verbose_name="Ad Soyad")
    phone = models.CharField(max_length=20, verbose_name="Telefon", blank=True, null=True)
    email = models.EmailField(verbose_name="E-posta", blank=True, null=True)
    tax_id = models.CharField(max_length=20, verbose_name="T.C. Kimlik No / Vergi No", blank=True, null=True)
    risk_profile = models.CharField(
        max_length=20, 
        verbose_name="Risk Profili",
        choices=[
            ('low', 'Düşük Risk'),
            ('medium', 'Orta Risk'),
            ('high', 'Yüksek Risk'),
        ],
        default='medium'
    )
    investment_goal = models.TextField(verbose_name="Yatırım Hedefi", blank=True, null=True)
    notes = models.TextField(verbose_name="Notlar", blank=True, null=True)
    
    # Finansal bilgiler
    total_invested = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0, 
        verbose_name="Toplam Yatırım Tutarı"
    )
    start_date = models.DateField(verbose_name="Yatırım Başlangıç Tarihi", null=True, blank=True)
    monthly_contribution = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Aylık Katkı",
        help_text="Yatırımcının aylık düzenli yatırım tutarı"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Kayıt Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Yatırımcı"
        verbose_name_plural = "Yatırımcılar"
        ordering = ['name']
    
    @property
    def current_portfolio_value(self):
        """Yatırımcının tüm fon paylarının güncel toplam değeri"""
        return sum(share.current_value for share in self.fund_shares.all())
    
    @property
    def profit_loss(self):
        """Yatırımcının toplam kar/zarar miktarı"""
        return self.current_portfolio_value - self.total_invested
    
    @property
    def profit_loss_percentage(self):
        """Yatırımcının kar/zarar yüzdesi"""
        if self.total_invested == 0:
            return 0
        return (self.profit_loss / self.total_invested) * 100
    
    def update_investment_total(self):
        """İşlem (Transaction) kayıtlarından toplam yatırımı hesaplar"""
        
        # Tüm portföylerdeki işlemleri al
        portfolios = self.portfolios.all()
        portfolio_ids = [p.id for p in portfolios]
        
        # Elle hesapla - transaction tablosundan
        total_invested = 0
        transactions = Transaction.objects.filter(portfolio_id__in=portfolio_ids)
        
        for tx in transactions:
            if tx.transaction_type == 'buy':
                # Alış işleminde toplam tutarı ekle
                total_invested += (tx.price * tx.quantity) + tx.commission + tx.tax
            elif tx.transaction_type == 'sell':
                # Satış işleminde toplam tutarı çıkar
                total_invested -= (tx.price * tx.quantity) - tx.commission - tx.tax
        
        self.total_invested = total_invested
        self.save(update_fields=['total_invested'])
        
        return self.total_invested

    def update_total_investment(self):
        """Yatırım Girişlerinden (Investment) toplam yatırımı hesaplar"""
        total = self.investments.aggregate(total=models.Sum('amount'))['total'] or 0
        self.total_invested = total
        self.save(update_fields=['total_invested'])
        return self.total_invested
        
    def calculate_combined_investment(self):
        """Hem işlemleri hem de yatırım girişlerini hesaba katar"""
        # Bu gelecekte eklenebilir
        pass

# Yatırım girişlerini takip eden model
class Investment(models.Model):
    """Yatırımcının yaptığı nakit girişlerini (para yatırmalarını) takip eder"""
    INVESTMENT_TYPES = [
        ('initial', 'İlk Yatırım'),
        ('additional', 'Ek Yatırım'),
        ('monthly', 'Düzenli Aylık Yatırım'),
        ('dividend', 'Temettü Yeniden Yatırımı'),
        ('bonus', 'Bonus/Prim'),
    ]
    
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='investments', verbose_name="Yatırımcı")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Yatırım Tutarı")
    date = models.DateField(verbose_name="Yatırım Tarihi")
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPES, default='additional', verbose_name="Yatırım Tipi")
    notes = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Kayıt Tarihi")
    
    def __str__(self):
        return f"{self.investor.name} - {self.amount} TL ({self.date})"
    
    class Meta:
        verbose_name = "Yatırım Girişi"
        verbose_name_plural = "Yatırım Girişleri"
        ordering = ['-date']
    
    def save(self, *args, **kwargs):
        # Önce kaydı oluşturalım, sonra toplam yatırımı güncelleyelim
        super().save(*args, **kwargs)
        
        # Veritabanı işleminin tamamlanması için bir transaction kullanıyoruz
        transaction.on_commit(lambda: self.update_investor_total())
    
    def delete(self, *args, **kwargs):
        # Silinmeden önce yatırımcı referansını sakla
        investor_id = self.investor_id
        
        # Kaydı sil
        result = super().delete(*args, **kwargs)
        
        # Silme işlemi tamamlandıktan sonra yatırımcıyı doğrudan güncelle
        try:
            from .models import Investor
            investor = Investor.objects.get(id=investor_id)
            
            # Yatırımcının toplam yatırımını yeniden hesapla
            total = Investment.objects.filter(investor_id=investor_id).aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            
            investor.total_invested = total
            investor.save(update_fields=['total_invested'])
        except Exception as e:
            print(f"Yatırımcı güncellenirken hata: {e}")
        
        return result
    
    def update_investor_total(self):
        """Yatırımcının toplam yatırım tutarını, TÜM yatırım girişlerini toplayarak günceller"""
        investor = self.investor
        
        # Tüm Investment nesnelerini tekrar sorgula ve topla
        connection.cursor().execute("SELECT 1")
        
        # Yeni bir sorgu ile tüm yatırım girişlerini topla
        investments = Investment.objects.filter(investor=investor)
        total_amount = investments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Yatırımcının toplam yatırımını güncelle
        investor.total_invested = total_amount
        investor.save(update_fields=['total_invested'])
        
        return investor.total_invested

# Fund modeli - Yatırım fonu bilgileri
class Fund(models.Model):
    name = models.CharField(max_length=100, verbose_name="Fon Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    creation_date = models.DateField(verbose_name="Oluşturma Tarihi")
    currency = models.CharField(max_length=3, default="TRY", verbose_name="Para Birimi", 
                              choices=[('TRY', 'Türk Lirası'), ('USD', 'Amerikan Doları'), ('EUR', 'Euro')])
    management_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Yönetim Ücreti (%)")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    
    # Risk seviyesi
    RISK_LEVELS = [
        ('low', 'Düşük Risk'),
        ('medium', 'Orta Risk'),
        ('high', 'Yüksek Risk'),
    ]
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='medium', verbose_name="Risk Seviyesi")
    
    # Hedef getiri
    target_return = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, 
                                      verbose_name="Hedef Getiri (%)")
    
    # Fon değerleri
    initial_value = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Başlangıç Değeri")
    current_value = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Güncel Değer")
    
    # Zaman damgaları
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Zamanı")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Zamanı")
    
    # Toplam pay adedi
    total_shares = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Toplam Pay Adedi")
    
    def __str__(self):
        return f"{self.name} ({self.current_value} {self.currency})"
    
    class Meta:
        verbose_name = "Fon"
        verbose_name_plural = "Fonlar"
        ordering = ['-creation_date']
    
    @property
    def total_return(self):
        """Fonun toplam getirisi (%)"""
        # None kontrolü ekleyelim
        current = self.current_value or 0
        initial = self.initial_value or 0
        
        if initial == 0:
            return 0
        return ((current - initial) / initial) * 100
    
    @property
    def total_return_amount(self):
        """Fonun toplam getirisi (miktar)"""
        # None kontrolü ekleyelim
        current = self.current_value or 0
        initial = self.initial_value or 0
        return current - initial 
    
    @property
    def share_value(self):
        """Birim pay değeri"""
        if self.total_shares == 0:
            return 0
        return self.current_value / self.total_shares

    def update_value_from_portfolios(self):
        """Fon değerini bağlı portföylerin değerlerini toplayarak günceller"""
        # Bağlı tüm portföylerin değerlerini topla
        total_portfolio_value = sum(portfolio.total_current_value for portfolio in self.portfolios.all())
        
        # Güncel değeri güncelle (ama pay değerini korumak için bir hesaplama yap)
        if self.total_shares > 0:
            # Önceki pay değerini hesapla
            prev_share_value = self.current_value / self.total_shares
            
            # Yeni değer
            self.current_value = total_portfolio_value
            
            # Yeni pay değeri değişimi yüzdesini hesapla
            if prev_share_value > 0:
                new_share_value = self.current_value / self.total_shares
                change_percent = (new_share_value / prev_share_value - 1) * 100
                print(f"Fon değer değişimi: %{change_percent:.2f}")
        else:
            # Payı yoksa sadece değeri güncelle
            self.current_value = total_portfolio_value
            
        # Değişiklikleri kaydet
        self.save(update_fields=['current_value'])
        return self.current_value

# Fon Payı modeli - Yatırımcıların fon paylarını izler
class FundShare(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='shares', verbose_name="Fon")
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='fund_shares', verbose_name="Yatırımcı")
    
    # Pay bilgileri
    shares_count = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Pay Adedi")
    initial_investment = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Yatırım Tutarı")
    entry_date = models.DateField(verbose_name="Giriş Tarihi")
    
    # İzleme alanları
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Son Güncelleme")
    notes = models.TextField(blank=True, null=True, verbose_name="Notlar")
    
    def __str__(self):
        return f"{self.investor.name} - {self.fund.name} ({self.shares_count} pay)"
    
    class Meta:
        verbose_name = "Fon Payı"
        verbose_name_plural = "Fon Payları"
        unique_together = ('fund', 'investor')  # Bir yatırımcının bir fonda tek bir payı olabilir
    
    def save(self, *args, **kwargs):
        # Mevcut kaydı kontrol et
        if not self._state.adding and self.pk:
            # Eski versiyonu veritabanından al
            old_instance = FundShare.objects.get(pk=self.pk)
            
            # Değiştirilemez alanları eski değerleriyle koruyalım
            if old_instance.shares_count != self.shares_count:
                # Pay adedini otomatik hesaplıyoruz, elle değiştirmeye izin vermiyoruz
                pass  # Hesaplama aşağıda yapılacak
            
            # Yatırım değiştiyse, payı yeniden hesapla
            if old_instance.initial_investment != self.initial_investment:
                # Yatırım tutarı değiştiğinde payları yeniden hesapla
                if self.initial_investment > 0:
                    if self.fund.total_shares > 0:
                        # Güncel pay değerini kullan
                        share_value = self.fund.current_value / self.fund.total_shares
                    else:
                        share_value = Decimal('1')
                    
                    # Pay değerinden pay adedini hesapla
                    self.shares_count = self.initial_investment / share_value
                else:
                    self.shares_count = Decimal('0')
        else:  # Yeni kayıt
            # Pay adedini hesapla
            if self.initial_investment > 0:
                if self.fund.total_shares > 0:
                    share_value = self.fund.current_value / self.fund.total_shares
                else:
                    share_value = Decimal('1')
                
                self.shares_count = self.initial_investment / share_value
            else:
                self.shares_count = Decimal('0')
        
        # Normal kaydetme işlemini yap
        super().save(*args, **kwargs)
        
    @property
    def current_value(self):
        """Payların güncel değeri"""
        # Fon pay değerini hesapla (toplam değer / toplam pay adedi)
        total_shares = self.fund.total_shares
        
        if total_shares == 0:
            return 0
            
        share_value = self.fund.current_value / total_shares
        return self.shares_count * share_value 

    @property
    def profit_loss(self):
        """Kar/zarar miktarı"""
        return self.current_value - self.initial_investment
    
    @property
    def profit_loss_percentage(self):
        """Kar/zarar yüzdesi"""
        if self.initial_investment > 0:
            return (self.profit_loss / self.initial_investment) * 100
        return 0 