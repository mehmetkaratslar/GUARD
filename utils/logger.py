# =======================================================================================
# 📄 Dosya Adı   : logger.py
# 📁 Konum       : guard_pc/utils/logger.py
# 📌 Açıklama    : Gelişmiş loglama sistemi
#                 - Dosya ve konsol çıktısı
#                 - Log seviyeleri ve filtreleme
#                 - Rotating file handler
#                 - Formatlanmış çıktılar
#
# 🔗 Bağlantılı Dosyalar:
#   - config/settings.py : Log ayarları
#   - main.py           : Ana uygulama logging'i
#   - Tüm servisler     : Hata ve bilgi logları
# =======================================================================================

import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from config.settings import Settings

class ColoredFormatter(logging.Formatter):
    """Renkli konsol çıktısı için formatter"""
    
    # ANSI renk kodları
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Renk kodunu ekle
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        
        # Formatter'ı uygula
        return super().format(record)

class JsonFormatter(logging.Formatter):
    """JSON formatında log çıktısı"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Exception bilgisi varsa ekle
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Extra alanları ekle
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message']:
                log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)

class GuardLogger:
    """Guard uygulaması için özel logger sınıfı"""
    
    def __init__(self, name: str = "guard"):
        """Logger'ı başlatır"""
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Duplicate handler'ları önle
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Handler'ları ayarlar"""
        # Logs dizini oluştur
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Console handler
        self._setup_console_handler()
        
        # File handler
        self._setup_file_handler()
        
        # Error file handler
        self._setup_error_handler()
        
        # JSON handler (opsiyonel)
        if Settings.DEBUG:
            self._setup_json_handler()
    
    def _setup_console_handler(self):
        """Konsol çıktısı handler'ı"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Platform kontrolü - Windows'da renk desteği
        if sys.platform == "win32":
            try:
                import colorama
                colorama.init()
                formatter = ColoredFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S'
                )
            except ImportError:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S'
                )
        else:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Dosya çıktısı handler'ı"""
        file_handler = logging.handlers.RotatingFileHandler(
            Settings.LOG_FILE_PATH,
            maxBytes=Settings.LOG_MAX_SIZE,
            backupCount=Settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _setup_error_handler(self):
        """Hata dosyası handler'ı"""
        error_file = "logs/guard_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d\n'
            'Message: %(message)s\n'
            'Function: %(funcName)s\n'
            '%(pathname)s:%(lineno)d\n'
            '%(exc_text)s\n' + '-'*50,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def _setup_json_handler(self):
        """JSON formatı handler'ı"""
        json_file = "logs/guard_json.log"
        json_handler = logging.handlers.RotatingFileHandler(
            json_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=2,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        
        formatter = JsonFormatter()
        json_handler.setFormatter(formatter)
        self.logger.addHandler(json_handler)
    
    def debug(self, message: str, **kwargs):
        """Debug seviyesi log"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Info seviyesi log"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning seviyesi log"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exc_info: bool = True, **kwargs):
        """Error seviyesi log"""
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """Critical seviyesi log"""
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Exception log (otomatik exc_info=True)"""
        self.logger.exception(message, extra=kwargs)
    
    def log_function_call(self, func_name: str, args: tuple = None, kwargs: dict = None):
        """Fonksiyon çağrısını loglar"""
        call_info = {
            'function': func_name,
            'args': str(args) if args else None,
            'kwargs': str(kwargs) if kwargs else None
        }
        self.debug(f"Function called: {func_name}", **call_info)
    
    def log_performance(self, operation: str, duration: float, **context):
        """Performans metriklerini loglar"""
        perf_info = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            **context
        }
        self.info(f"Performance: {operation} took {duration:.3f}s", **perf_info)
    
    def log_user_action(self, user_id: str, action: str, **details):
        """Kullanıcı eylemlerini loglar"""
        action_info = {
            'user_id': user_id,
            'action': action,
            **details
        }
        self.info(f"User action: {action}", **action_info)
    
    def log_system_event(self, event_type: str, **details):
        """Sistem olaylarını loglar"""
        event_info = {
            'event_type': event_type,
            **details
        }
        self.info(f"System event: {event_type}", **event_info)

class PerformanceLogger:
    """Performans ölçümü için context manager"""
    
    def __init__(self, logger: GuardLogger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            if exc_type:
                self.logger.error(
                    f"Operation failed: {self.operation}",
                    exc_info=(exc_type, exc_val, exc_tb),
                    **self.context
                )
            else:
                self.logger.log_performance(self.operation, duration, **self.context)

def setup_logging(log_level: str = None, enable_json: bool = False):
    """Global logging'i ayarlar"""
    if log_level is None:
        log_level = Settings.LOG_LEVEL
    
    # Root logger'ı yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Diğer kütüphanelerin log seviyelerini ayarla
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('firebase_admin').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    
    return GuardLogger()

# Global logger instance
_guard_logger = None

def get_logger(name: str = "guard") -> GuardLogger:
    """Global logger instance'ını döndürür"""
    global _guard_logger
    if _guard_logger is None:
        _guard_logger = GuardLogger(name)
    return _guard_logger

def log_exception(logger: GuardLogger, message: str = "An error occurred"):
    """Exception decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"{message} in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator

def performance_monitor(logger: GuardLogger, operation_name: str = None):
    """Performans monitoring decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with PerformanceLogger(logger, op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Yardımcı fonksiyonlar
def cleanup_old_logs(days: int = 30):
    """Eski log dosyalarını temizler"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_file in logs_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                print(f"Eski log dosyası silindi: {log_file}")
                
    except Exception as e:
        print(f"Log temizliği sırasında hata: {str(e)}")

def get_log_stats() -> dict:
    """Log istatistiklerini döndürür"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return {"error": "Logs directory not found"}
        
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "files": []
        }
        
        for log_file in logs_dir.glob("*.log*"):
            file_size = log_file.stat().st_size
            stats["total_files"] += 1
            stats["total_size_mb"] += file_size / (1024 * 1024)
            
            stats["files"].append({
                "name": log_file.name,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats
        
    except Exception as e:
        return {"error": str(e)}

# Test fonksiyonu
def test_logger():
    """Logger'ı test eder"""
    logger = get_logger("test")
    
    logger.info("Test başladı")
    logger.debug("Debug mesajı")
    logger.warning("Uyarı mesajı")
    
    try:
        # Hata oluştur
        1 / 0
    except Exception as e:
        logger.exception("Test exception")
    
    # Performans testi
    with PerformanceLogger(logger, "test_operation", test_param="value"):
        import time
        time.sleep(0.1)
    
    logger.log_user_action("test_user", "login", ip="127.0.0.1")
    logger.log_system_event("startup", version="1.0.0")
    
    print("Log stats:", get_log_stats())

if __name__ == "__main__":
    test_logger()