# =======================================================================================
# 📄 Dosya Adı   : auth_service.py
# 📁 Konum       : guard_pc/services/auth_service.py
# 📌 Açıklama    : Firebase Authentication ve Google OAuth entegrasyonu
#                 - Google ile giriş/kayıt işlemleri
#                 - Kullanıcı oturum yönetimi
#                 - Token doğrulama ve yenileme
#
# 🔗 Bağlantılı Dosyalar:
#   - config/firebase_config.py : Firebase bağlantısı
#   - config/settings.py        : Google OAuth ayarları
#   - ui/login_window.py        : Giriş ekranı ile etkileşim
#   - services/database_service.py : Kullanıcı verilerini kaydetme
# =======================================================================================

import logging
import json
import time
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs
import requests
from typing import Optional, Dict, Callable
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

from config.settings import Settings

class AuthService:
    """Firebase Authentication ve Google OAuth servisi"""
    
    def __init__(self):
        self.current_user = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        self.is_authenticated = False
        
        # OAuth callback server
        self.callback_server = None
        self.callback_port = 3000
        self.auth_code = None
        self.auth_callback = None
        
        # Firebase REST API endpoints
        self.firebase_base_url = f"https://identitytoolkit.googleapis.com/v1/accounts"
        self.api_key = Settings.FIREBASE_API_KEY
        
    def start_oauth_flow(self, success_callback: Callable = None, error_callback: Callable = None):
        """Google OAuth akışını başlatır"""
        try:
            self.auth_callback = success_callback
            
            # Callback server'ı başlat
            self._start_callback_server()
            
            # Google OAuth URL'sini oluştur
            oauth_url = self._build_oauth_url()
            
            logging.info("Google OAuth akışı başlatılıyor...")
            logging.info(f"OAuth URL: {oauth_url}")
            
            # Tarayıcıda OAuth URL'sini aç
            webbrowser.open(oauth_url)
            
            return True
            
        except Exception as e:
            logging.error(f"OAuth akışı başlatılırken hata: {str(e)}")
            if error_callback:
                error_callback(str(e))
            return False
    
    def _build_oauth_url(self) -> str:
        """Google OAuth URL'sini oluşturur"""
        params = {
            'client_id': Settings.GOOGLE_CLIENT_ID,
            'redirect_uri': Settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account'
        }
        
        param_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        return f"https://accounts.google.com/o/oauth2/auth?{param_string}"
    
    def _start_callback_server(self):
        """OAuth callback için HTTP server başlatır"""
        try:
            class OAuthCallbackHandler(BaseHTTPRequestHandler):
                def __init__(self, auth_service_instance):
                    self.auth_service = auth_service_instance
                    
                def __call__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                
                def do_GET(self):
                    try:
                        # URL'den authorization code'u al
                        parsed_url = urlparse(self.path)
                        query_params = parse_qs(parsed_url.query)
                        
                        if 'code' in query_params:
                            self.auth_service.auth_code = query_params['code'][0]
                            
                            # Başarı sayfası gönder
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            
                            success_html = """
                            <html>
                            <head><title>Guard - Giriş Başarılı</title></head>
                            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                                <h2 style="color: green;">✅ Giriş Başarılı!</h2>
                                <p>Tarayıcıyı kapatabilir ve Guard uygulamasına dönebilirsiniz.</p>
                            </body>
                            </html>
                            """
                            self.wfile.write(success_html.encode())
                            
                            # Auth code ile token al
                            threading.Thread(target=self.auth_service._handle_auth_code).start()
                            
                        elif 'error' in query_params:
                            error = query_params['error'][0]
                            logging.error(f"OAuth hatası: {error}")
                            
                            # Hata sayfası gönder
                            self.send_response(400)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            
                            error_html = f"""
                            <html>
                            <head><title>Guard - Giriş Hatası</title></head>
                            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                                <h2 style="color: red;">❌ Giriş Hatası</h2>
                                <p>Hata: {error}</p>
                                <p>Lütfen tekrar deneyin.</p>
                            </body>
                            </html>
                            """
                            self.wfile.write(error_html.encode())
                            
                    except Exception as e:
                        logging.error(f"Callback handler hatası: {str(e)}")
                
                def log_message(self, format, *args):
                    # HTTP server loglarını sustur
                    pass
            
            # Boş port bul
            self.callback_port = self._find_free_port()
            
            # Server'ı başlat
            handler = OAuthCallbackHandler(self)
            self.callback_server = HTTPServer(('localhost', self.callback_port), handler)
            
            # Server'ı ayrı thread'de çalıştır
            server_thread = threading.Thread(target=self.callback_server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            logging.info(f"OAuth callback server başlatıldı: http://localhost:{self.callback_port}")
            
        except Exception as e:
            logging.error(f"Callback server başlatılırken hata: {str(e)}")
            raise e
    
    def _find_free_port(self) -> int:
        """Boş port bulur"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _handle_auth_code(self):
        """Authorization code ile access token alır"""
        try:
            if not self.auth_code:
                logging.error("Authorization code bulunamadı")
                return
            
            logging.info("Authorization code ile token alınıyor...")
            
            # Google'dan access token al
            token_data = self._exchange_code_for_token(self.auth_code)
            
            if token_data:
                # Google'dan kullanıcı bilgilerini al
                user_info = self._get_user_info(token_data['access_token'])
                
                if user_info:
                    # Firebase Custom Token oluştur (veya direkt kullanıcı bilgilerini kullan)
                    self._handle_successful_auth(user_info, token_data)
                    
            # Callback server'ı kapat
            if self.callback_server:
                self.callback_server.shutdown()
                
        except Exception as e:
            logging.error(f"Auth code işleminde hata: {str(e)}")
    
    def _exchange_code_for_token(self, auth_code: str) -> Optional[Dict]:
        """Authorization code'u access token ile değiştirir"""
        try:
            token_url = "https://oauth2.googleapis.com/token"
            
            data = {
                'client_id': Settings.GOOGLE_CLIENT_ID,
                'client_secret': Settings.GOOGLE_CLIENT_SECRET,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': Settings.GOOGLE_REDIRECT_URI
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            logging.info("Access token başarıyla alındı")
            
            return token_data
            
        except Exception as e:
            logging.error(f"Token değişiminde hata: {str(e)}")
            return None
    
    def _get_user_info(self, access_token: str) -> Optional[Dict]:
        """Google'dan kullanıcı bilgilerini alır"""
        try:
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(user_info_url, headers=headers)
            response.raise_for_status()
            
            user_info = response.json()
            logging.info(f"Kullanıcı bilgileri alındı: {user_info.get('email')}")
            
            return user_info
            
        except Exception as e:
            logging.error(f"Kullanıcı bilgileri alınırken hata: {str(e)}")
            return None
    
    def _handle_successful_auth(self, user_info: Dict, token_data: Dict):
        """Başarılı authentication'ı işler"""
        try:
            # Kullanıcı bilgilerini kaydet
            self.current_user = {
                'uid': user_info['id'],
                'email': user_info['email'],
                'name': user_info.get('name', ''),
                'picture': user_info.get('picture', ''),
                'verified_email': user_info.get('verified_email', False)
            }
            
            # Token bilgilerini kaydet
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            # Token süresini hesapla
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = time.time() + expires_in
            
            self.is_authenticated = True
            
            logging.info(f"Kullanıcı başarıyla giriş yaptı: {self.current_user['email']}")
            
            # Success callback'i çağır
            if self.auth_callback:
                self.auth_callback(self.current_user)
                
        except Exception as e:
            logging.error(f"Başarılı auth işleminde hata: {str(e)}")
    
    def logout(self):
        """Kullanıcıyı çıkış yapar"""
        try:
            logging.info(f"Kullanıcı çıkış yapıyor: {self.current_user.get('email', 'Unknown') if self.current_user else 'Unknown'}")
            
            # Token'ları iptal et
            if self.access_token:
                self._revoke_token()
            
            # Kullanıcı bilgilerini temizle
            self.current_user = None
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = 0
            self.is_authenticated = False
            
            logging.info("Çıkış işlemi tamamlandı")
            return True
            
        except Exception as e:
            logging.error(f"Çıkış yaparken hata: {str(e)}")
            return False
    
    def _revoke_token(self):
        """Access token'ı iptal eder"""
        try:
            if self.access_token:
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={self.access_token}"
                requests.post(revoke_url)
                logging.info("Access token iptal edildi")
                
        except Exception as e:
            logging.warning(f"Token iptal edilirken hata: {str(e)}")
    
    def refresh_access_token(self) -> bool:
        """Access token'ı yeniler"""
        try:
            if not self.refresh_token:
                logging.warning("Refresh token bulunamadı")
                return False
            
            token_url = "https://oauth2.googleapis.com/token"
            
            data = {
                'client_id': Settings.GOOGLE_CLIENT_ID,
                'client_secret': Settings.GOOGLE_CLIENT_SECRET,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Yeni token bilgilerini güncelle
            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = time.time() + expires_in
            
            logging.info("Access token yenilendi")
            return True
            
        except Exception as e:
            logging.error(f"Token yenileme hatası: {str(e)}")
            return False
    
    def is_token_expired(self) -> bool:
        """Token'ın süresi dolmuş mu kontrol eder"""
        if not self.access_token or not self.token_expires_at:
            return True
        
        # 5 dakika önce süresinin dolacağını varsay
        return time.time() >= (self.token_expires_at - 300)
    
    def ensure_valid_token(self) -> bool:
        """Geçerli bir token olduğundan emin olur"""
        if not self.is_authenticated:
            return False
        
        if self.is_token_expired():
            return self.refresh_access_token()
        
        return True
    
    def get_current_user(self) -> Optional[Dict]:
        """Mevcut kullanıcı bilgilerini döndürür"""
        return self.current_user
    
    def get_user_id(self) -> Optional[str]:
        """Mevcut kullanıcının ID'sini döndürür"""
        return self.current_user['uid'] if self.current_user else None
    
    def is_user_authenticated(self) -> bool:
        """Kullanıcının giriş yapmış olup olmadığını kontrol eder"""
        return self.is_authenticated and self.current_user is not None

# Global auth service instance'ı
_auth_service_instance = None

def get_auth_service() -> AuthService:
    """Global AuthService instance'ını döndürür"""
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance