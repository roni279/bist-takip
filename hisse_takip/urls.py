from django.urls import path
from . import views

app_name = 'hisse_takip'

urlpatterns = [
    # Dashboard
    path('', views.home_view, name='home'),
    
    # Portföy yönetimi
    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/<int:pk>/', views.portfolio_detail, name='portfolio_detail'),
    path('portfolios/add/', views.portfolio_add, name='portfolio_add'),
    path('portfolios/<int:pk>/edit/', views.portfolio_edit, name='portfolio_edit'),
    
    # Hisse senedi görünümleri
    path('stocks/', views.stock_list, name='stock_list'),
    path('stocks/<str:code>/', views.stock_detail, name='stock_detail'),
    path('stocks/watchlist/', views.watchlist, name='watchlist'),
    
    # İşlem yönetimi
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.transaction_add, name='transaction_add'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    
    # Raporlar
    path('reports/performance/', views.performance_report, name='performance_report'),
    path('reports/summary/', views.summary_report, name='summary_report'),
    
    # Ayarlar
    path('settings/', views.settings_view, name='settings'),
    
    # Yatırımcı Dashboard
    path('investor/', views.investor_dashboard, name='investor_dashboard'),
] 