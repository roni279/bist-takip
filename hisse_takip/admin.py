from django.contrib import admin
from .models import (
    Stock, PriceData, Portfolio, Position, Transaction, 
    WatchList, WatchListItem, Alert, PortfolioSnapshot, Investor, Investment, Fund, FundShare
)

# Mevcut kayıtlar
@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    list_filter = ['code']

@admin.register(PriceData)
class PriceDataAdmin(admin.ModelAdmin):
    list_display = ['stock', 'price', 'change_percentage', 'update_time', 'timestamp', 'is_positive']
    list_filter = ['stock', 'timestamp', 'update_time']
    search_fields = ['stock__code', 'stock__name']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']

# Portföy Yönetimi
@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['name', 'investor', 'user', 'fund', 'created_at', 'is_active', 'total_current_value']
    list_filter = ['is_active', 'created_at', 'investor', 'fund']
    search_fields = ['name', 'description', 'investor__name', 'fund__name']
    date_hierarchy = 'created_at'
    
    # Fieldsets'e fund alanını ekleyelim
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'description', 'user', 'investor', 'fund')
        }),
        ('Finansal Ayarlar', {
            'fields': ('currency', 'target_return', 'risk_level', 'is_active')
        }),
    )
    
    # İsteğe bağlı: Fon değiştiğinde otomatik işlem
    def save_model(self, request, obj, form, change):
        # Eski fon referansını saklayalım
        if change and 'fund' in form.changed_data:
            old_fund_id = Portfolio.objects.get(pk=obj.pk).fund_id
        else:
            old_fund_id = None
            
        # Portföyü kaydet
        super().save_model(request, obj, form, change)
        
        # Eski ve yeni fonları güncelle
        if change and 'fund' in form.changed_data:
            # Eğer eski fon varsa, onun değerini güncelle
            if old_fund_id:
                try:
                    old_fund = Fund.objects.get(pk=old_fund_id)
                    old_fund.update_value_from_portfolios()
                except Fund.DoesNotExist:
                    pass
            
            # Yeni fonu güncelle
            if obj.fund:
                obj.fund.update_value_from_portfolios()

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['stock', 'portfolio', 'quantity', 'average_cost', 'current_price', 
                   'current_value', 'profit_loss', 'profit_loss_percentage', 'is_open']
    list_filter = ['portfolio', 'is_open']
    search_fields = ['stock__code', 'portfolio__name']
    date_hierarchy = 'open_date'
    readonly_fields = ['current_price', 'current_value', 'profit_loss', 'profit_loss_percentage']
    
    # Pozisyon sayfasında ilgili işlemleri gösterme
    fieldsets = (
        ('Pozisyon Bilgileri', {
            'fields': ('portfolio', 'stock', 'quantity', 'average_cost', 'open_date', 'is_open')
        }),
        ('Güncel Durum', {
            'fields': ('current_price', 'current_value', 'profit_loss', 'profit_loss_percentage'),
        }),
        ('Ek Bilgiler', {
            'fields': ('target_price', 'stop_loss', 'notes'),
            'classes': ('collapse',),
        }),
    )
    
    def current_price(self, obj):
        return obj.current_price
    current_price.short_description = 'Güncel Fiyat'
    
    def current_value(self, obj):
        return obj.current_value
    current_value.short_description = 'Güncel Değer'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'stock', 'portfolio', 'date', 'price', 'quantity', 'total_amount']
    list_filter = ['transaction_type', 'portfolio', 'stock']
    search_fields = ['stock__code', 'portfolio__name']
    date_hierarchy = 'date'
    
    # İşlem ekleme formunu özelleştirme
    fieldsets = (
        ('İşlem Bilgileri', {
            'fields': ('portfolio', 'stock', 'transaction_type', 'date', 'price', 'quantity')
        }),
        ('Ek Bilgiler', {
            'fields': ('commission', 'tax', 'notes'),
            'classes': ('collapse',),
        }),
    )
    
    # İşlem ekleme sayfasında portföye göre filtreli stok seçimi eklenebilir
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # İşlem kaydedildiğinde portföy değerini güncelleme
        from django.utils import timezone
        from .models import PortfolioSnapshot
        
        # Portföy snap'i oluştur
        snapshot, created = PortfolioSnapshot.objects.get_or_create(
            portfolio=obj.portfolio,
            date=timezone.now().date(),
            defaults={
                'total_value': obj.portfolio.total_current_value,
                'total_cost': obj.portfolio.total_cost,
                'profit_loss': obj.portfolio.total_profit_loss,
                'profit_loss_percentage': obj.portfolio.profit_loss_percentage,
                'benchmark_comparison': None  # Buraya benchmark hesaplaması eklenebilir
            }
        )
        
        if not created:
            # Eğer günün snapshot'ı zaten varsa güncelle
            snapshot.total_value = obj.portfolio.total_current_value
            snapshot.total_cost = obj.portfolio.total_cost
            snapshot.profit_loss = obj.portfolio.total_profit_loss
            snapshot.profit_loss_percentage = obj.portfolio.profit_loss_percentage
            snapshot.save()

# İzleme ve Alarmlar
@admin.register(WatchList)
class WatchListAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    list_filter = ['user']
    search_fields = ['name', 'user__username']
    date_hierarchy = 'created_at'

@admin.register(WatchListItem)
class WatchListItemAdmin(admin.ModelAdmin):
    list_display = ['stock', 'watchlist', 'target_price', 'added_at']
    list_filter = ['watchlist']
    search_fields = ['stock__code', 'watchlist__name']
    date_hierarchy = 'added_at'

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['stock', 'user', 'condition_type', 'threshold_value', 'is_active', 'notification_sent']
    list_filter = ['condition_type', 'is_active', 'notification_sent', 'user']
    search_fields = ['stock__code', 'user__username']
    date_hierarchy = 'created_at'

# Performans Takibi
@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'date', 'total_value', 'profit_loss_percentage', 'benchmark_comparison']
    list_filter = ['portfolio']
    search_fields = ['portfolio__name']
    date_hierarchy = 'date'

# Yatırımcı sayfasında yatırımları göstermek için inline
class InvestmentInline(admin.TabularInline):
    model = Investment
    extra = 1  # Boş bir satır ekle
    fields = ['date', 'amount', 'investment_type', 'notes']

@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'total_invested', 'current_portfolio_value', 'profit_loss_percentage', 'risk_profile', 'created_at']
    search_fields = ['name', 'email', 'phone']
    list_filter = ['risk_profile', 'created_at']
    
    # created_at ve updated_at alanlarını da readonly olarak ekleyeceğiz
    readonly_fields = ['total_invested', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Kişisel Bilgiler', {
            'fields': ('name', 'user', 'email', 'phone', 'tax_id')
        }),
        ('Finansal Bilgiler', {
            'fields': ('total_invested', 'start_date', 'monthly_contribution', 'risk_profile')
        }),
        ('Ek Bilgiler', {
            'fields': ('investment_goal', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def current_portfolio_value(self, obj):
        return obj.current_portfolio_value
    current_portfolio_value.short_description = 'Güncel Portföy Değeri'
    
    def profit_loss_percentage(self, obj):
        return f"%{obj.profit_loss_percentage:.2f}"
    profit_loss_percentage.short_description = 'Kar/Zarar Yüzdesi'
    
    # Yatırımcı sayfasında yatırımları göster
    inlines = [InvestmentInline]
    
    # Toplam yatırımı yeniden hesaplamak için bir eylem ekle
    actions = ['update_from_transactions', 'recalculate_from_investments']
    
    def update_from_transactions(self, request, queryset):
        updated = 0
        for investor in queryset:
            investor.update_investment_total()
            updated += 1
        self.message_user(request, f"{updated} yatırımcının toplam yatırım tutarı işlemlerden yeniden hesaplandı.")
    update_from_transactions.short_description = "Seçili yatırımcıların toplam yatırımını İŞLEMLERDEN hesapla"
    
    def recalculate_from_investments(self, request, queryset):
        updated = 0
        for investor in queryset:
            investor.update_total_investment()
            updated += 1
        self.message_user(request, f"{updated} yatırımcının toplam yatırım tutarı, yatırım girişlerinden yeniden hesaplandı.")
    recalculate_from_investments.short_description = "Seçili yatırımcıların toplam yatırımını YATIRIM GİRİŞLERİNDEN hesapla"

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['investor', 'amount', 'date', 'investment_type', 'notes']
    list_filter = ['investment_type', 'date', 'investor']
    search_fields = ['investor__name', 'notes']
    date_hierarchy = 'date'
    
    # Form üzerinde kolay erişim için alanları düzenli göster
    fieldsets = (
        ('Yatırım Bilgileri', {
            'fields': ('investor', 'amount', 'date', 'investment_type')
        }),
        ('Ek Bilgiler', {
            'fields': ('notes',),
        }),
    )
    
    def delete_model(self, request, obj):
        # Silmeden önce yatırımcı referansını sakla
        investor = obj.investor
        
        # Nesneyi sil
        super().delete_model(request, obj)
        
        # Yatırımcının toplam yatırımını güncelle
        investor.update_total_investment()
    
    def delete_queryset(self, request, queryset):
        # Toplu silme için tüm etkilenen yatırımcıları bul
        investor_ids = set(queryset.values_list('investor_id', flat=True))
        
        # Nesneleri sil
        super().delete_queryset(request, queryset)
        
        # Etkilenen tüm yatırımcıların toplam yatırımlarını güncelle
        from .models import Investor
        for investor_id in investor_ids:
            try:
                investor = Investor.objects.get(id=investor_id)
                investor.update_total_investment()
            except Exception as e:
                print(f"Yatırımcı {investor_id} güncellenirken hata: {e}")

# FundShare için inline admin
class FundShareInline(admin.TabularInline):
    model = FundShare
    extra = 1
    fk_name = 'fund'
    fields = ['investor', 'initial_investment', 'entry_date', 'current_value', 'notes']
    readonly_fields = ['current_value']
    
    def get_readonly_fields(self, request, obj=None):
        # Her durumda readonly olması gereken alanlar  
        readonly_fields = ['current_value']
        
        # Eğer mevcut bir kayıt düzenleniyor ve admin süper kullanıcı değilse
        if obj and not request.user.is_superuser:
            # Yatırımcıya da değişiklik yapılamasın
            readonly_fields.append('investor')
        
        return readonly_fields
    
    def current_value(self, obj):
        if obj.id:
            return obj.current_value
        return "-"
    current_value.short_description = "Güncel Değer"

@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ['name', 'creation_date', 'current_value', 'currency', 'total_return', 'risk_level', 'is_active']
    list_filter = ['is_active', 'risk_level', 'currency', 'creation_date']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_return', 'share_value']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'description', 'creation_date', 'currency', 'is_active')
        }),
        ('Risk ve Getiri', {
            'fields': ('risk_level', 'target_return')
        }),
        ('Finansal Bilgiler', {
            'fields': ('initial_value', 'current_value', 'total_shares', 'share_value', 'total_return')
        }),
        ('Yönetim', {
            'fields': ('management_fee',)
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_return(self, obj):
        try:
            return f"%{obj.total_return:.2f}"
        except (TypeError, ValueError):
            return "Hesaplanamadı"
    total_return.short_description = 'Toplam Getiri'
    
    def share_value(self, obj):
        try:
            return f"{obj.share_value:.2f} {obj.currency}"
        except:
            return "Hesaplanamadı"
    share_value.short_description = "Birim Pay Değeri"
    
    # Yatırımcı sayfasında yatırımları göster
    inlines = [FundShareInline]

# FundShare modelini admin paneline ekle
@admin.register(FundShare)
class FundShareAdmin(admin.ModelAdmin):
    list_display = ['investor', 'fund', 'shares_count', 'initial_investment', 'current_value', 'entry_date']
    list_filter = ['fund', 'investor', 'entry_date']
    search_fields = ['investor__name', 'fund__name', 'notes']
    readonly_fields = ['current_value', 'last_updated', 'shares_count']
    
    # Admin formunu özelleştir
    fieldsets = (
        ('Yatırımcı Bilgileri', {
            'fields': ('investor', 'fund', 'initial_investment', 'entry_date')
        }),
        ('Otomatik Hesaplanan Değerler', {
            'fields': ('shares_count', 'current_value'),
            'classes': ('collapse',),
            'description': 'Bu değerler otomatik hesaplanır ve değiştirilemez.'
        }),
        ('Ek Bilgiler', {
            'fields': ('notes', 'last_updated'),
            'classes': ('collapse',),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        # Her durumda readonly olması gereken alanlar
        readonly_fields = ['current_value', 'last_updated', 'shares_count']
        
        # Eğer mevcut bir kayıt düzenleniyor ve admin süper kullanıcı değilse
        if obj and not request.user.is_superuser:
            # Fona ve yatırımcıya da değişiklik yapılamasın
            readonly_fields.extend(['fund', 'investor'])
        
        return readonly_fields
    
    # Form kaydedilirken kontrol et
    def save_model(self, request, obj, form, change):
        # Değişen alan varsa
        if change:
            # Eski kaydı al
            old_obj = FundShare.objects.get(pk=obj.pk)
            
            # Eğer değiştirilemez alan değişmişse uyarı ver
            if 'shares_count' in form.changed_data:
                # Pay adedi değiştirilmeye çalışılıyorsa, bunu engelle
                # Burada form.cleaned_data'dan shares_count'u kaldırabiliriz
                obj.shares_count = old_obj.shares_count
        
        super().save_model(request, obj, form, change) 