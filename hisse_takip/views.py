from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from .models import Portfolio, Stock, Transaction, WatchList, Position, Investor, Fund, FundShare
from django.contrib.auth import logout

# Create your views here.

# Geçici bir şablon sayfası oluşturulana kadar kullanılacak
def under_construction(request, view_name="Bu sayfa"):
    return HttpResponse(f"""
        <div style="text-align:center; margin-top:100px; font-family:Arial;">
            <h1>Geliştirme Devam Ediyor</h1>
            <p>{view_name} yapım aşamasındadır.</p>
            <p><a href="/">Ana sayfaya dön</a></p>
        </div>
    """)

# Dashboard
@login_required
def dashboard(request):
    # İleride burada kullanıcının portföyleri, izleme listeleri ve özet bilgileri gösterilecek
    context = {
        'title': 'Dashboard',
    }
    # Şablon dosyası oluşturulduktan sonra render(request, 'hisse_takip/dashboard.html', context) kullanılacak
    return under_construction(request, "Dashboard")

# Portföy Görünümleri
@login_required
def portfolio_list(request):
    # İleride burada kullanıcının portföylerinin listesi gösterilecek
    return under_construction(request, "Portföy Listesi")

@login_required
def portfolio_detail(request, pk):
    # İleride burada belirli bir portföyün detayları gösterilecek
    return under_construction(request, f"Portföy Detayı (ID: {pk})")

@login_required
def portfolio_add(request):
    # İleride burada yeni portföy ekleme formu gösterilecek
    return under_construction(request, "Portföy Ekleme")

@login_required
def portfolio_edit(request, pk):
    # İleride burada portföy düzenleme formu gösterilecek
    return under_construction(request, f"Portföy Düzenleme (ID: {pk})")

# Hisse Senedi Görünümleri
@login_required
def stock_list(request):
    # İleride burada hisse senetleri listelenecek
    return under_construction(request, "Hisse Senedi Listesi")

@login_required
def stock_detail(request, code):
    # İleride burada belirli bir hisse senedinin detayları gösterilecek
    return under_construction(request, f"Hisse Detayı (Kod: {code})")

@login_required
def watchlist(request):
    # İleride burada kullanıcının izleme listesi gösterilecek
    return under_construction(request, "İzleme Listesi")

# İşlem Görünümleri
@login_required
def transaction_list(request):
    # İleride burada işlemler listelenecek
    return under_construction(request, "İşlem Listesi")

@login_required
def transaction_add(request):
    # İleride burada yeni işlem ekleme formu gösterilecek
    return under_construction(request, "İşlem Ekleme")

@login_required
def transaction_detail(request, pk):
    # İleride burada belirli bir işlemin detayları gösterilecek
    return under_construction(request, f"İşlem Detayı (ID: {pk})")

# Rapor Görünümleri
@login_required
def performance_report(request):
    # İleride burada performans raporu gösterilecek
    return under_construction(request, "Performans Raporu")

@login_required
def summary_report(request):
    # İleride burada özet rapor gösterilecek
    return under_construction(request, "Özet Rapor")

# Ayarlar
@login_required
def settings_view(request):
    # İleride burada ayarlar sayfası gösterilecek
    return under_construction(request, "Ayarlar")

# İleride Yatırımcı Dashboard'u için Görünüm
@login_required
def investor_dashboard(request):
    """
    Bir yatırımcının fon paylarını ve portföylerini gösteren dashboard.
    """
    # Kullanıcıya bağlı yatırımcı bilgilerini al
    if hasattr(request.user, 'investor') and request.user.investor:
        investor = request.user.investor
        
        # Yatırımcının fon paylarını al
        fund_shares = investor.fund_shares.all()
        
        # Toplam değerleri hesapla
        total_current_value = sum(share.current_value for share in fund_shares)
        total_initial_investment = sum(share.initial_investment for share in fund_shares)
        total_profit_loss = total_current_value - total_initial_investment
        
        # Yüzde hesaplama (sıfıra bölme kontrolü ile)
        if total_initial_investment > 0:
            total_profit_percentage = (total_profit_loss / total_initial_investment) * 100
        else:
            total_profit_percentage = 0
            
        context = {
            'investor': investor,
            'fund_shares': fund_shares,
            'total_current_value': total_current_value,
            'total_initial_investment': total_initial_investment,
            'total_profit_loss': total_profit_loss,
            'total_profit_percentage': total_profit_percentage,
        }
        
        return render(request, 'hisse_takip/investor_dashboard.html', context)
    else:
        # Eğer kullanıcıya bağlı yatırımcı yoksa
        messages.warning(request, "Yatırımcı bilgileriniz bulunamadı. Lütfen yönetici ile iletişime geçin.")
        return render(request, 'hisse_takip/investor_dashboard.html', {
            'fund_shares': [],
            'total_current_value': 0,
            'total_initial_investment': 0,
            'total_profit_loss': 0,
            'total_profit_percentage': 0,
        })

def home_view(request):
    """
    Ana sayfaya erişen kullanıcılar için yönlendirme view'ı
    """
    if request.user.is_authenticated:
        # Oturum açılmışsa investor dashboard'a yönlendir
        return redirect('hisse_takip:investor_dashboard')
    else:
        # Oturum açılmamışsa login sayfasına yönlendir
        return redirect('login')

def custom_logout(request):
    """
    Hem GET hem de POST istekleri için çalışan çıkış fonksiyonu
    """
    logout(request)
    return redirect('login')
