# =======================================================================================
# 📄 Dosya Adı   : main.py
# 📁 Konum       : guard_pc/main.py
# 📌 Açıklama    : Guard PC uygulaması ana giriş noktası
#                 - Uygulama başlatma ve kaynak yönetimi
#                 - Global logging yapılandırması
#                 - Firebase ve servis başlatma
#                 - GUI başlatma
#
# 🔗 Bağlantılı Dosyalar:
#   - config/              : Tüm yapılandırma dosyaları
#   - services/            : Tüm servis dosyaları
#   - ui/                  : GUI dosyaları
#   - models/              : AI modeli
# =======================================================================================

import sys
import os
import logging
import signal
import atexit
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Logging sistemini yapılandırır"""
    from config.settings import Settings
    
    # Logs dizinini oluştur
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Log formatı
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger'ı yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Settings.LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            Settings.LOG_FILE_PATH,
            maxBytes=Settings.LOG_MAX_SIZE,
            backupCount=Settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        
        logging.info("Log sistemi başlatıldı")
        
    except Exception as e:
        logging.warning(f"File handler oluşturulamadı: {str(e)}")

def check_requirements():
    """Gerekli bağımlılıkları kontrol eder"""
    missing_packages = []
    
    # Kritik paketleri kontrol et
    required_packages = [
        'cv2',
        'torch',
        'ultralytics',
        'firebase_admin',
        'flask',
        'tkinter'
    ]
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'tkinter':
                import tkinter
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logging.error(f"Eksik paketler: {', '.join(missing_packages)}")
        logging.error("Lütfen 'pip install -r requirements.txt' komutunu çalıştırın")
        return False
    
    logging.info("Tüm gerekli paketler mevcut")
    return True

def initialize_services():
    """Temel servisleri başlatır"""
    try:
        # Ayarları doğrula
        from config.settings import Settings
        if not Settings.validate_settings():
            logging.warning("Bazı ayarlar eksik, bazı özellikler çalışmayabilir")
        
        # Firebase'i başlat
        from config.firebase_config import initialize_firebase
        firebase_success = initialize_firebase()
        
        if firebase_success:
            logging.info("Firebase başarıyla başlatıldı")
        else:
            logging.warning("Firebase başlatılamadı, yerel mod kullanılacak")
        
        # Fall detector'ı başlat
        from models.fall_detector import initialize_fall_detector
        model_success = initialize_fall_detector()
        
        if model_success:
            logging.info("Düşme tespit modeli başarıyla yüklendi")
        else:
            logging.error("Düşme tespit modeli yüklenemedi!")
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Servisler başlatılırken hata: {str(e)}")
        return False

def create_directories():
    """Gerekli dizinleri oluşturur"""
    directories = [
        "logs",
        "data/local_data",
        "assets/icons",
        "assets/images", 
        "assets/sounds"
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.warning(f"Dizin oluşturulamadı {directory}: {str(e)}")

def check_model_file():
    """Model dosyasının varlığını kontrol eder"""
    from config.settings import Settings
    
    model_path = Path(Settings.MODEL_PATH)
    
    if not model_path.exists():
        logging.error(f"Model dosyası bulunamadı: {model_path}")
        logging.error("Lütfen fall_model.pt dosyasını models/ klasörüne kopyalayın")
        return False
    
    logging.info(f"Model dosyası bulundu: {model_path}")
    return True

class GuardApplication:
    """Ana uygulama sınıfı"""
    
    def __init__(self):
        """Uygulamayı başlatır"""
        self.is_running = False
        self.services_initialized = False
        
        # Cleanup handler'ları kaydet
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logging.info("Guard uygulaması başlatılıyor...")
    
    def _signal_handler(self, signum, frame):
        """Sinyal yakalayıcı"""
        logging.info(f"Sinyal alındı: {signum}")
        self.cleanup()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """Uygulamayı başlatır"""
        try:
            # Dizinleri oluştur
            create_directories()
            
            # Gereksinimleri kontrol et
            if not check_requirements():
                return False
            
            # Model dosyasını kontrol et
            if not check_model_file():
                return False
            
            # Servisleri başlat
            if not initialize_services():
                return False
            
            self.services_initialized = True
            logging.info("Uygulama başarıyla başlatıldı")
            return True
            
        except Exception as e:
            logging.error(f"Uygulama başlatılırken hata: {str(e)}")
            return False
    
    def run_gui(self):
        """GUI'yi başlatır"""
        try:
            from ui.login_window import LoginWindow
            
            # Login penceresi oluştur ve çalıştır
            login_window = LoginWindow()
            login_window.run()
            
        except Exception as e:
            logging.error(f"GUI başlatılırken hata: {str(e)}")
            raise e
    
    def run(self):
        """Ana çalışma döngüsü"""
        try:
            if not self.initialize():
                logging.error("Uygulama başlatılamadı")
                return False
            
            self.is_running = True
            
            # GUI'yi başlat
            self.run_gui()
            
            return True
            
        except KeyboardInterrupt:
            logging.info("Kullanıcı tarafından durduruldu")
            return True
        except Exception as e:
            logging.error(f"Uygulama çalışırken hata: {str(e)}")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Kaynakları temizler"""
        if not self.is_running:
            return
        
        try:
            logging.info("Uygulama kapatılıyor, kaynaklar temizleniyor...")
            
            # Servisleri temizle
            self._cleanup_services()
            
            self.is_running = False
            logging.info("Uygulama başarıyla kapatıldı")
            
        except Exception as e:
            logging.error(f"Cleanup sırasında hata: {str(e)}")
    
    def _cleanup_services(self):
        """Servisleri temizler"""
        try:
            # Camera service'i temizle
            from services.camera_service import get_camera_service
            camera_service = get_camera_service()
            camera_service.cleanup()
            
            # Streaming service'i temizle
            from services.streaming_service import get_streaming_service
            streaming_service = get_streaming_service()
            streaming_service.cleanup()
            
            # Fall detector'ı temizle
            from models.fall_detector import get_fall_detector
            fall_detector = get_fall_detector()
            fall_detector.cleanup()
            
            logging.info("Tüm servisler temizlendi")
            
        except Exception as e:
            logging.error(f"Servisler temizlenirken hata: {str(e)}")

def main():
    """Ana fonksiyon"""
    # Logging'i başlat
    setup_logging()
    
    logging.info("="*60)
    logging.info("GUARD PC UYGULAMASI BAŞLATILIYOR")
    logging.info("="*60)
    
    try:
        # Uygulamayı oluştur ve çalıştır
        app = GuardApplication()
        success = app.run()
        
        if success:
            logging.info("Uygulama başarıyla tamamlandı")
            sys.exit(0)
        else:
            logging.error("Uygulama hata ile sonlandı")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logging.info("Kullanıcı tarafından durduruldu")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Beklenmeyen hata: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()