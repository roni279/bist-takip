from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages

class LoginRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Temel URL kontrolü
        if request.path == '/' and request.user.is_authenticated:
            # Kullanıcı giriş yapmışsa ana sayfada yönlendir
            return redirect('hisse_takip:investor_dashboard')
        
        # Korumalı sayfalara erişim kontrolü
        if request.path.startswith('/investor/') and not request.user.is_authenticated:
            # Login sayfasına yönlendir
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        
        # Investor kontrol - Eğer kullanıcı giriş yapmış ama yatırımcı değilse
        if request.user.is_authenticated and request.path.startswith('/investor/'):
            if not hasattr(request.user, 'investor') or not request.user.investor:
                # Mesaj ekle
                if not hasattr(request, '_messages'):
                    messages.warning(
                        request, 
                        "Yatırımcı hesabınız bulunmamaktadır. Lütfen yönetici ile iletişime geçin."
                    )
                # Yönlendirme yapmayıp devam edelim (view'da zaten kontrol var)
        
        # Diğer middleware'lere geçiş
        response = self.get_response(request)
        return response 