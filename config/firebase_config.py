# =======================================================================================
# 📄 Dosya Adı   : firebase_config.py
# 📁 Konum       : guard_pc/config/firebase_config.py
# 📌 Açıklama    : Firebase Admin SDK yapılandırması ve bağlantı yönetimi
#                 - Firebase Admin SDK'yi başlatır
#                 - Firestore ve Storage bağlantılarını sağlar
#                 - Bağlantı hatalarını yönetir ve yerel çalışma moduna geçer
#
# 🔗 Bağlantılı Dosyalar:
#   - config/settings.py        : Firebase ayarları
#   - services/auth_service.py  : Authentication servisi
#   - services/database_service.py : Firestore servisi
#   - services/storage_service.py  : Storage servisi
# =======================================================================================

import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, storage
from config.settings import Settings

class FirebaseConfig:
    """Firebase yapılandırma ve bağlantı yönetimi sınıfı"""
    
    def __init__(self):
        self.app = None
        self.db = None
        self.storage_bucket = None
        self.is_connected = False
        
        # Firebase servis hesabı anahtarı yolu
        self.service_account_path = "config/firebase_service_account.json"
        
    def initialize_firebase(self):
        """Firebase Admin SDK'yi başlatır"""
        try:
            # Firebase zaten başlatılmışsa tekrar başlatma
            if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
                logging.info("Firebase zaten başlatılmış")
                self.app = firebase_admin.get_app()
                self.is_connected = True
                self._initialize_services()
                return True
            
            # Servis hesabı anahtarı dosyasını kontrol et
            if os.path.exists(self.service_account_path):
                # Servis hesabı anahtarı ile başlat
                cred = credentials.Certificate(self.service_account_path)
                self.app = firebase_admin.initialize_app(cred, {
                    'storageBucket': Settings.FIREBASE_STORAGE_BUCKET,
                    'databaseURL': Settings.FIREBASE_DATABASE_URL
                })
                logging.info("Firebase Admin SDK servis hesabı ile başlatıldı")
            else:
                # Varsayılan kimlik bilgileri ile başlat (Google Cloud ortamında)
                try:
                    cred = credentials.ApplicationDefault()
                    self.app = firebase_admin.initialize_app(cred, {
                        'storageBucket': Settings.FIREBASE_STORAGE_BUCKET,
                        'databaseURL': Settings.FIREBASE_DATABASE_URL
                    })
                    logging.info("Firebase Admin SDK varsayılan kimlik bilgileri ile başlatıldı")
                except Exception as e:
                    logging.warning(f"Varsayılan kimlik bilgileri bulunamadı: {str(e)}")
                    # Çevre değişkenleri ile başlatmayı dene
                    return self._initialize_with_env_vars()
            
            self.is_connected = True
            self._initialize_services()
            return True
            
        except Exception as e:
            logging.error(f"Firebase başlatılırken hata oluştu: {str(e)}")
            logging.info("Yerel çalışma moduna geçiliyor...")
            self.is_connected = False
            return False
    
    def _initialize_with_env_vars(self):
        """Çevre değişkenleri ile Firebase'i başlatmaya çalışır"""
        try:
            # Firebase yapılandırmasını çevre değişkenlerinden oluştur
            firebase_config = {
                "type": "service_account",
                "project_id": Settings.FIREBASE_PROJECT_ID,
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            # Gerekli alanları kontrol et
            required_fields = ["project_id", "private_key", "client_email"]
            missing_fields = [field for field in required_fields if not firebase_config.get(field)]
            
            if missing_fields:
                logging.warning(f"Eksik Firebase yapılandırması: {', '.join(missing_fields)}")
                return False
            
            cred = credentials.Certificate(firebase_config)
            self.app = firebase_admin.initialize_app(cred, {
                'storageBucket': Settings.FIREBASE_STORAGE_BUCKET,
                'databaseURL': Settings.FIREBASE_DATABASE_URL
            })
            
            logging.info("Firebase Admin SDK çevre değişkenleri ile başlatıldı")
            return True
            
        except Exception as e:
            logging.error(f"Çevre değişkenleri ile Firebase başlatılamadı: {str(e)}")
            return False
    
    def _initialize_services(self):
        """Firebase servislerini başlatır"""
        try:
            # Firestore istemcisini başlat
            self.db = firestore.client()
            logging.info("Firestore istemcisi başlatıldı")
            
            # Storage bucket'ını başlat
            self.storage_bucket = storage.bucket()
            logging.info("Firebase Storage başlatıldı")
            
        except Exception as e:
            logging.error(f"Firebase servisleri başlatılırken hata: {str(e)}")
            self.is_connected = False
    
    def get_firestore_client(self):
        """Firestore istemcisini döndürür"""
        if not self.is_connected:
            logging.warning("Firebase bağlantısı yok, Firestore istemcisi döndürülemiyor")
            return None
        return self.db
    
    def get_storage_bucket(self):
        """Storage bucket'ını döndürür"""
        if not self.is_connected:
            logging.warning("Firebase bağlantısı yok, Storage bucket döndürülemiyor")
            return None
        return self.storage_bucket
    
    def test_connection(self):
        """Firebase bağlantısını test eder"""
        try:
            if not self.is_connected:
                return False
            
            # Firestore bağlantısını test et
            if self.db:
                # Basit bir okuma işlemi yap
                test_doc = self.db.collection('test').document('connection_test')
                test_doc.get()
                logging.info("Firestore bağlantısı test edildi - OK")
            
            # Storage bağlantısını test et
            if self.storage_bucket:
                # Bucket varlığını kontrol et
                self.storage_bucket.exists()
                logging.info("Firebase Storage bağlantısı test edildi - OK")
            
            return True
            
        except Exception as e:
            logging.error(f"Firebase bağlantı testi başarısız: {str(e)}")
            self.is_connected = False
            return False
    
    def create_service_account_template(self):
        """Firebase servis hesabı anahtar dosyası şablonu oluşturur"""
        template_path = "config/firebase_service_account_template.json"
        template_content = """{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID",
  "private_key_id": "YOUR_PRIVATE_KEY_ID",
  "private_key": "YOUR_PRIVATE_KEY",
  "client_email": "YOUR_CLIENT_EMAIL",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "YOUR_CLIENT_CERT_URL"
}"""
        
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            logging.info(f"Firebase servis hesabı şablonu oluşturuldu: {template_path}")
            logging.info("Firebase Console'dan indirdiğiniz servis hesabı anahtarını 'firebase_service_account.json' adıyla kaydedin")
            
        except Exception as e:
            logging.error(f"Şablon dosyası oluşturulamadı: {str(e)}")

# Global Firebase yapılandırma instance'ı
firebase_config = FirebaseConfig()

def get_firebase_app():
    """Firebase app instance'ını döndürür"""
    return firebase_config.app

def get_firestore_client():
    """Firestore istemcisini döndürür"""
    return firebase_config.get_firestore_client()

def get_storage_bucket():
    """Storage bucket'ını döndürür"""
    return firebase_config.get_storage_bucket()

def is_firebase_connected():
    """Firebase bağlantı durumunu döndürür"""
    return firebase_config.is_connected

def initialize_firebase():
    """Firebase'i başlatır"""
    return firebase_config.initialize_firebase()

def test_firebase_connection():
    """Firebase bağlantısını test eder"""
    return firebase_config.test_connection()