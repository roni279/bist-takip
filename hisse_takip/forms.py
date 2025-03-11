from django import forms
from django.utils import timezone
from .models import (
    Portfolio, Transaction, Stock, Position, 
    WatchList, WatchListItem, Fund, FundShare, Investor
)
from decimal import Decimal

# Portföy Formları
class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name', 'description', 'investor', 'fund', 'currency', 'target_return', 'risk_level', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'target_return': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sadece etkin yatırımcıları göster
        self.fields['investor'].queryset = Investor.objects.filter(is_active=True)
        # Sadece etkin fonları göster
        self.fields['fund'].queryset = Fund.objects.filter(is_active=True)
        # Kullanıcıya göre filtreleme eklenebilir
        
    def clean(self):
        cleaned_data = super().clean()
        # İstenirse portföy adı benzersizlik kontrolü eklenebilir
        return cleaned_data

# İşlem Formları
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['portfolio', 'stock', 'transaction_type', 'quantity', 'price', 'date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'step': '1'}),
        }
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Kullanıcının portföylerini filtrele
        self.fields['portfolio'].queryset = Portfolio.objects.filter(user=user)
        # Form ilk açıldığında bugünkü tarihi varsayılan olarak ayarla
        if not self.instance.pk:  # Yeni kayıt ise
            self.initial['date'] = timezone.now().date()
    
    def clean_quantity(self):
        """Miktar doğrulama"""
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise forms.ValidationError("Miktar pozitif bir değer olmalıdır.")
        return quantity
    
    def clean_price(self):
        """Fiyat doğrulama"""
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("Fiyat pozitif bir değer olmalıdır.")
        return price
    
    def clean(self):
        """Form seviyesinde doğrulama"""
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')
        portfolio = cleaned_data.get('portfolio')
        stock = cleaned_data.get('stock')
        
        # Satış işlemi için pozisyon kontrolü
        if transaction_type == 'SELL' and portfolio and stock and quantity:
            try:
                position = Position.objects.get(portfolio=portfolio, stock=stock)
                if position.quantity < quantity:
                    self.add_error('quantity', 'Sahip olduğunuzdan daha fazla hisse satamazsınız.')
            except Position.DoesNotExist:
                self.add_error('stock', 'Bu hissede pozisyonunuz bulunmuyor.')
        
        return cleaned_data

# İzleme Listesi Formları
class WatchListForm(forms.ModelForm):
    class Meta:
        model = WatchList
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class WatchListItemForm(forms.ModelForm):
    class Meta:
        model = WatchListItem
        fields = ['stock', 'target_price', 'alert_on_target']
        widgets = {
            'target_price': forms.NumberInput(attrs={'step': '0.01'}),
        }

# Fon Formları
class FundForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ['name', 'description', 'currency', 'start_date', 'target_return', 
                 'risk_level', 'management_fee', 'is_active', 'icon']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'target_return': forms.NumberInput(attrs={'step': '0.01'}),
            'management_fee': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def clean_management_fee(self):
        """Yönetim ücreti doğrulama"""
        fee = self.cleaned_data.get('management_fee')
        if fee < 0 or fee > 10:
            raise forms.ValidationError("Yönetim ücreti %0-%10 arasında olmalıdır.")
        return fee

# Fon Payı Formları
class FundShareForm(forms.ModelForm):
    class Meta:
        model = FundShare
        fields = ['investor', 'fund', 'initial_investment', 'entry_date', 'notes']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'initial_investment': forms.NumberInput(attrs={'step': '0.01'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Form ilk açıldığında bugünkü tarihi varsayılan olarak ayarla
        if not self.instance.pk:  # Yeni kayıt ise
            self.initial['entry_date'] = timezone.now().date()
    
    def clean_initial_investment(self):
        """Yatırım tutarı doğrulama"""
        investment = self.cleaned_data.get('initial_investment')
        if investment <= 0:
            raise forms.ValidationError("Yatırım tutarı pozitif bir değer olmalıdır.")
        return investment

# Yatırımcı Formları
class InvestorForm(forms.ModelForm):
    class Meta:
        model = Investor
        fields = ['name', 'email', 'phone', 'address', 'tax_id', 'identity_number', 
                 'birth_date', 'risk_profile', 'is_active', 'notes']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def clean_email(self):
        """Email doğrulama"""
        email = self.cleaned_data.get('email')
        # Eğer bu email ile başka bir yatırımcı varsa
        if self.instance.pk:  # Düzenleme durumu
            if Investor.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Bu e-posta adresi başka bir yatırımcı tarafından kullanılıyor.")
        else:  # Yeni kayıt
            if Investor.objects.filter(email=email).exists():
                raise forms.ValidationError("Bu e-posta adresi başka bir yatırımcı tarafından kullanılıyor.")
        return email

# Arama Formları
class StockSearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=False, label="Arama",
                           widget=forms.TextInput(attrs={'placeholder': 'Hisse Kodu veya Şirket Adı'}))
    
class TransactionSearchForm(forms.Form):
    TRANSACTION_TYPE_CHOICES = [('', 'Tüm İşlemler')] + list(Transaction.TRANSACTION_CHOICES)
    
    start_date = forms.DateField(required=False, label="Başlangıç Tarihi", 
                                widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, label="Bitiş Tarihi",
                              widget=forms.DateInput(attrs={'type': 'date'}))
    transaction_type = forms.ChoiceField(choices=TRANSACTION_TYPE_CHOICES, required=False, label="İşlem Tipi")
    stock = forms.ModelChoiceField(queryset=Stock.objects.all(), required=False, label="Hisse")
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', "Bitiş tarihi başlangıç tarihinden önce olamaz.")
        
        return cleaned_data 