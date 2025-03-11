import requests
import os
from django.conf import settings

class CollectAPIClient:
    def __init__(self, api_key=None):
        # API anahtarını doğrudan alın veya environmental variable'dan okuyun
        self.api_key = api_key or os.environ.get('COLLECT_API_KEY')
        self.base_url = "https://api.collectapi.com/economy"
        
    def get_currency_data(self):
        """Döviz verilerini çeker - Bu endpointin çalıştığını biliyoruz"""
        endpoint = f"{self.base_url}/currencyToAll"
        
        headers = {
            'content-type': 'application/json',
            'authorization': 'apikey ' + self.api_key
        }
        
        params = {
            'int': '10',
            'base': 'USD'
        }
        
        try:
            print(f"Döviz API isteği gönderiliyor: {endpoint}")
            
            response = requests.get(endpoint, headers=headers, params=params)
            
            print(f"API yanıt kodu: {response.status_code}")
            
            if response.status_code != 200:
                print(f"API yanıt detayı: {response.text}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API isteği sırasında hata oluştu: {e}")
            return None
            
    def get_bist_data(self):
        """BIST verilerini çeker - Bu endpoint hesabınızda aktif olmayabilir"""
        endpoint = f"{self.base_url}/hisseSenedi"
        
        headers = {
            'content-type': 'application/json',
            'authorization': 'apikey ' + self.api_key
        }
        
        try:
            print(f"BIST API isteği gönderiliyor: {endpoint}")
            
            response = requests.get(endpoint, headers=headers)
            
            print(f"API yanıt kodu: {response.status_code}")
            
            if response.status_code != 200:
                print(f"API yanıt detayı: {response.text}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API isteği sırasında hata oluştu: {e}")
            return None 