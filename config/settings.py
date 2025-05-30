# =======================================================================================
# 📄 Dosya Adı   : settings.py
# 📁 Konum       : guard_pc/config/settings.py
# 📌 Açıklama    : Guard PC uygulaması temel yapılandırma ayarları
#                 - .env dosyasından çevre değişkenlerini yükler
#                 - Uygulama genelinde kullanılan sabit değerleri tanımlar
#                 - Firebase, kamera, model ve streaming ayarları
#
# 🔗 Bağlantılı Dosyalar:
#   - .env                    : Çevre değişkenleri
#   - config/firebase_config.py : Firebase bağlantı ayarları
#   - services/              : Tüm servis dosyaları bu ayarları kullanır
# =======================================================================================

import os
from dotenv import load_dotenv
import logging

# .env dosyasını yükle
load_dotenv()

class Settings:
    """Uygulama ayarları sınıfı"""
    
    # ==================== UYGULAMA AYARLARI ====================
    APP_NAME = os.getenv("APP_NAME", "Guard")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ==================== FIREBASE AYARLARI ====================
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
    FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
    FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")
    
    # ==================== SMTP AYARLARI ====================
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    
    # ==================== TWILIO AYARLARI ====================
    TWILIO_SID = os.getenv("TWILIO_SID")
    TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE")
    
    # ==================== TELEGRAM AYARLARI ====================
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # ==================== GOOGLE OAUTH AYARLARI ====================
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000")
    
    # ==================== KAMERA AYARLARI ====================
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
    CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "640"))
    CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "480"))
    CAMERA_FPS = int(os.getenv("CAMERA_FPS", "30"))
    
    # ==================== MODEL AYARLARI ====================
    MODEL_PATH = os.getenv("MODEL_PATH", "models/fall_model.pt")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    DETECTION_INTERVAL = float(os.getenv("DETECTION_INTERVAL", "0.1"))
    
    # ==================== STREAMING AYARLARI ====================
    STREAMING_PORT = int(os.getenv("STREAMING_PORT", "8080"))
    STREAMING_HOST = os.getenv("STREAMING_HOST", "0.0.0.0")
    RTSP_PORT = int(os.getenv("RTSP_PORT", "8554"))
    
    # ==================== VERİTABANI AYARLARI ====================
    LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "data/local_data")
    BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", "3600"))
    
    # ==================== GUI AYARLARI ====================
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    
    # Tema ayarları
    THEME_MODE = "dark"  # "dark", "light" veya "system"
    THEME_COLOR = "blue"  # "blue", "green", "dark-blue"
    
    # ==================== LOG AYARLARI ====================
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_PATH = "logs/guard.log"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # ==================== GÜVENLİK AYARLARI ====================
    SESSION_TIMEOUT = 24 * 60 * 60  # 24 saat (saniye)
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_TIME = 15 * 60  # 15 dakika (saniye)
    
    # ==================== BİLDİRİM AYARLARI ====================
    # Varsayılan bildirim ayarları
    DEFAULT_NOTIFICATION_SETTINGS = {
        "email_notification": True,
        "sms_notification": False,
        "telegram_notification": False,
        "phone_notification": False,
        "sound_notification": True,
        "desktop_notification": True
    }
    
    # ==================== OLAY AYARLARI ====================
    # Düşme tespiti için ayarlar
    FALL_DETECTION_COOLDOWN = 5  # Saniye - aynı kişi için tekrar tespit aralığı
    MAX_EVENT_STORAGE_DAYS = 30  # Olayları ne kadar süre saklayacağı
    AUTO_DELETE_OLD_EVENTS = True
    
    # ==================== PERFORMANS AYARLARI ====================
    MAX_CONCURRENT_DETECTIONS = 1  # Aynı anda kaç tespit işlemi
    FRAME_SKIP_COUNT = 2  # Performans için frame atlama
    GPU_ACCELERATION = True  # CUDA kullanılsın mı
    
    @classmethod
    def validate_settings(cls):
        """Ayarları doğrular ve eksik olanları bildirir"""
        required_settings = [
            'FIREBASE_PROJECT_ID',
            'SMTP_USER',
            'SMTP_PASS'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not getattr(cls, setting):
                missing_settings.append(setting)
        
        if missing_settings:
            logging.warning(f"Eksik ayarlar: {', '.join(missing_settings)}")
            return False
        
        logging.info("Tüm temel ayarlar doğrulandı")
        return True
    
    @classmethod
    def get_firebase_config(cls):
        """Firebase yapılandırmasını dict olarak döndürür"""
        return {
            "apiKey": cls.FIREBASE_API_KEY,
            "authDomain": cls.FIREBASE_AUTH_DOMAIN,
            "databaseURL": cls.FIREBASE_DATABASE_URL,
            "projectId": cls.FIREBASE_PROJECT_ID,
            "storageBucket": cls.FIREBASE_STORAGE_BUCKET,
            "messagingSenderId": cls.FIREBASE_MESSAGING_SENDER_ID,
            "appId": cls.FIREBASE_APP_ID
        }
    
    @classmethod
    def get_camera_config(cls):
        """Kamera yapılandırmasını dict olarak döndürür"""
        return {
            "index": cls.CAMERA_INDEX,
            "width": cls.CAMERA_WIDTH,
            "height": cls.CAMERA_HEIGHT,
            "fps": cls.CAMERA_FPS
        }
    
    @classmethod
    def get_model_config(cls):
        """Model yapılandırmasını dict olarak döndürür"""
        return {
            "path": cls.MODEL_PATH,
            "confidence_threshold": cls.CONFIDENCE_THRESHOLD,
            "detection_interval": cls.DETECTION_INTERVAL,
            "gpu_acceleration": cls.GPU_ACCELERATION
        }
    
    @classmethod
    def get_streaming_config(cls):
        """Streaming yapılandırmasını dict olarak döndürür"""
        return {
            "host": cls.STREAMING_HOST,
            "port": cls.STREAMING_PORT,
            "rtsp_port": cls.RTSP_PORT
        }