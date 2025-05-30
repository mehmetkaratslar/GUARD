# =======================================================================================
# 📄 Dosya Adı   : helpers.py
# 📁 Konum       : guard_pc/utils/helpers.py
# 📌 Açıklama    : Genel yardımcı fonksiyonlar ve utilities
#                 - Dosya işlemleri
#                 - Tarih/saat formatları
#                 - Validasyon fonksiyonları
#                 - Sistem bilgileri
#
# 🔗 Bağlantılı Dosyalar:
#   - Tüm proje dosyaları : Ortak yardımcı fonksiyonlar
#   - config/settings.py  : Ayar doğrulama
#   - services/           : Veri işleme yardımcıları
# =======================================================================================

import os
import sys
import platform
import psutil
import socket
import hashlib
import uuid
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import subprocess
import shutil
import threading
import time
import cv2
import numpy as np
from urllib.parse import urlparse
import requests

def get_system_info() -> Dict[str, Any]:
    """Sistem bilgilerini döndürür"""
    try:
        return {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'disk_free_gb': round(shutil.disk_usage('/').free / (1024**3), 2) if os.name != 'nt' 
                           else round(shutil.disk_usage('C:').free / (1024**3), 2)
        }
    except Exception as e:
        return {'error': str(e)}

def get_network_info() -> Dict[str, Any]:
    """Ağ bilgilerini döndürür"""
    try:
        # Yerel IP adresini al
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Hostname
        hostname = socket.gethostname()
        
        # Internet bağlantısını kontrol et
        internet_connected = check_internet_connection()
        
        return {
            'local_ip': local_ip,
            'hostname': hostname,
            'internet_connected': internet_connected
        }
    except Exception as e:
        return {'error': str(e)}

def check_internet_connection(timeout: int = 5) -> bool:
    """Internet bağlantısını kontrol eder"""
    try:
        requests.get('https://www.google.com', timeout=timeout)
        return True
    except requests.RequestException:
        return False

def validate_email(email: str) -> bool:
    """E-posta adresini doğrular"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone_number(phone: str) -> bool:
    """Telefon numarasını doğrular (uluslararası format)"""
    # Basit regex - gerçek uygulamada daha kapsamlı olabilir
    pattern = r'^\+?[1-9]\d{1,14}$'
    # Sadece rakam ve + karakterini al
    clean_phone = re.sub(r'[^\d+]', '', phone)
    return re.match(pattern, clean_phone) is not None

def validate_url(url: str) -> bool:
    """URL'nin geçerli olup olmadığını kontrol eder"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def format_datetime(timestamp: Union[float, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Timestamp'ı formatlar"""
    try:
        if isinstance(timestamp, float):
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = timestamp
        return dt.strftime(format_str)
    except Exception:
        return "Invalid date"

def format_duration(seconds: float) -> str:
    """Süreyi okunabilir formata çevirir"""
    try:
        if seconds < 60:
            return f"{seconds:.1f} saniye"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} dakika"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f} saat"
        else:
            days = seconds / 86400
            return f"{days:.1f} gün"
    except Exception:
        return "Invalid duration"

def format_file_size(bytes_size: int) -> str:
    """Dosya boyutunu okunabilir formata çevirir"""
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
    except Exception:
        return "Invalid size"

def generate_unique_id() -> str:
    """Benzersiz ID oluşturur"""
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """Kısa benzersiz ID oluşturur"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
    """Dosyanın hash değerini hesaplar"""
    try:
        hash_algo = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_algo.update(chunk)
        return hash_algo.hexdigest()
    except Exception:
        return None

def safe_json_load(file_path: str) -> Optional[Dict]:
    """JSON dosyasını güvenli şekilde yükler"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def safe_json_save(data: Dict, file_path: str) -> bool:
    """JSON verilerini güvenli şekilde kaydeder"""
    try:
        # Dizini oluştur
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Önce geçici dosyaya yaz
        temp_path = f"{file_path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Başarılıysa asıl dosyaya taşı
        shutil.move(temp_path, file_path)
        return True
    except Exception:
        return False

def ensure_directory(directory: str) -> bool:
    """Dizinin var olduğundan emin olur"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False

def get_available_cameras() -> List[int]:
    """Kullanılabilir kamera indekslerini döndürür"""
    available_cameras = []
    
    for i in range(10):  # 0-9 arası kontrol et
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Test frame'i al
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
            cap.release()
        except Exception:
            continue
    
    return available_cameras

def test_camera(camera_index: int, timeout: int = 5) -> Dict[str, Any]:
    """Kamerayı test eder"""
    try:
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return {'success': False, 'error': 'Camera could not be opened'}
        
        # Kamera bilgilerini al
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Test frame'i al
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return {'success': False, 'error': 'Could not read frame'}
        
        return {
            'success': True,
            'width': width,
            'height': height,
            'fps': fps,
            'frame_shape': frame.shape if frame is not None else None
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def resize_image_keep_aspect(image: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    """Görüntüyü oranını koruyarak yeniden boyutlandırır"""
    try:
        h, w = image.shape[:2]
        
        # Oranı hesapla
        aspect_ratio = w / h
        target_aspect = target_width / target_height
        
        if aspect_ratio > target_aspect:
            # Genişlik sınırlayıcı
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            # Yükseklik sınırlayıcı
            new_height = target_height
            new_width = int(target_height * aspect_ratio)
        
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
    except Exception:
        return image

def create_thumbnail(image: np.ndarray, size: Tuple[int, int] = (150, 150)) -> np.ndarray:
    """Görüntüden thumbnail oluşturur"""
    try:
        return resize_image_keep_aspect(image, size[0], size[1])
    except Exception:
        return image

def is_port_available(port: int, host: str = 'localhost') -> bool:
    """Port'un kullanılabilir olup olmadığını kontrol eder"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0  # 0 = bağlantı başarılı (port kullanımda)
    except Exception:
        return False

def find_free_port(start_port: int = 8000, end_port: int = 9000) -> Optional[int]:
    """Boş port bulur"""
    for port in range(start_port, end_port):
        if is_port_available(port):
            return port
    return None

def kill_process_on_port(port: int) -> bool:
    """Belirtilen portu kullanan process'i sonlandırır"""
    try:
        if platform.system() == "Windows":
            # Windows için netstat kullan
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid])
                        return True
        else:
            # Linux/Mac için lsof kullan
            result = subprocess.run(
                ["lsof", "-t", f"-i:{port}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                pid = result.stdout.strip()
                subprocess.run(["kill", "-9", pid])
                return True
                
        return False
        
    except Exception:
        return False

def debounce(wait_time: float):
    """Debounce decorator - fonksiyonun çok sık çağrılmasını önler"""
    def decorator(func):
        last_called = [0]
        
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if current_time - last_called[0] >= wait_time:
                last_called[0] = current_time
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def throttle(calls_per_second: float):
    """Throttle decorator - fonksiyonun saniyede max çağrı sayısını sınırlar"""
    def decorator(func):
        min_interval = 1.0 / calls_per_second
        last_called = [0]
        
        def wrapper(*args, **kwargs):
            current_time = time.time()
            elapsed = current_time - last_called[0]
            
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator - hata durumunda fonksiyonu tekrar dener"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise e
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator

def timeout(seconds: float):
    """Timeout decorator - fonksiyonun belirli sürede tamamlanmasını sağlar"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)
            
            if thread.is_alive():
                raise TimeoutError(f"Function timed out after {seconds} seconds")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    return decorator

class ConfigValidator:
    """Yapılandırma doğrulayıcı sınıfı"""
    
    @staticmethod
    def validate_firebase_config(config: Dict) -> Tuple[bool, List[str]]:
        """Firebase yapılandırmasını doğrular"""
        required_fields = [
            'apiKey', 'authDomain', 'projectId', 
            'storageBucket', 'messagingSenderId', 'appId'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not config.get(field):
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def validate_camera_config(config: Dict) -> Tuple[bool, List[str]]:
        """Kamera yapılandırmasını doğrular"""
        errors = []
        
        # Kamera indeksi
        camera_index = config.get('index', 0)
        if not isinstance(camera_index, int) or camera_index < 0:
            errors.append("Geçersiz kamera indeksi")
        
        # Çözünürlük
        width = config.get('width', 640)
        height = config.get('height', 480)
        
        if not isinstance(width, int) or width < 320 or width > 1920:
            errors.append("Geçersiz genişlik (320-1920 arası olmalı)")
        
        if not isinstance(height, int) or height < 240 or height > 1080:
            errors.append("Geçersiz yükseklik (240-1080 arası olmalı)")
        
        # FPS
        fps = config.get('fps', 30)
        if not isinstance(fps, (int, float)) or fps < 1 or fps > 60:
            errors.append("Geçersiz FPS (1-60 arası olmalı)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_notification_config(config: Dict) -> Tuple[bool, List[str]]:
        """Bildirim yapılandırmasını doğrular"""
        errors = []
        
        # E-posta
        if config.get('email_notification', False):
            email = config.get('email')
            if not email or not validate_email(email):
                errors.append("Geçersiz e-posta adresi")
        
        # SMS
        if config.get('sms_notification', False):
            phone = config.get('phone_number')
            if not phone or not validate_phone_number(phone):
                errors.append("Geçersiz telefon numarası")
        
        # Telegram
        if config.get('telegram_notification', False):
            chat_id = config.get('telegram_chat_id')
            if not chat_id or not str(chat_id).strip():
                errors.append("Geçersiz Telegram Chat ID")
        
        return len(errors) == 0, errors

class PerformanceMonitor:
    """Performans izleme sınıfı"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, name: str):
        """Timer başlatır"""
        self.start_times[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """Timer'ı bitirir ve süreyi döndürür"""
        if name in self.start_times:
            duration = time.time() - self.start_times[name]
            
            if name not in self.metrics:
                self.metrics[name] = []
            
            self.metrics[name].append(duration)
            del self.start_times[name]
            
            return duration
        return 0.0
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Performans istatistiklerini döndürür"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        times = self.metrics[name]
        return {
            'count': len(times),
            'total': sum(times),
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'last': times[-1]
        }
    
    def reset_metrics(self, name: str = None):
        """Metrikleri sıfırlar"""
        if name:
            self.metrics.pop(name, None)
        else:
            self.metrics.clear()
        self.start_times.clear()

class DataCache:
    """Basit veri önbellek sınıfı"""
    
    def __init__(self, default_ttl: int = 300):  # 5 dakika
        self.cache = {}
        self.timestamps = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Önbellekten veri alır"""
        if key not in self.cache:
            return None
        
        # TTL kontrolü
        if self._is_expired(key):
            self.delete(key)
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Önbelleğe veri ekler"""
        self.cache[key] = value
        self.timestamps[key] = time.time() + (ttl or self.default_ttl)
    
    def delete(self, key: str):
        """Önbellekten veri siler"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
    
    def clear(self):
        """Önbelleği temizler"""
        self.cache.clear()
        self.timestamps.clear()
    
    def _is_expired(self, key: str) -> bool:
        """Verinin süresi dolmuş mu kontrol eder"""
        return time.time() > self.timestamps.get(key, 0)
    
    def cleanup_expired(self):
        """Süresi dolmuş verileri temizler"""
        current_time = time.time()
        expired_keys = [
            key for key, expire_time in self.timestamps.items()
            if current_time > expire_time
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)

def sanitize_filename(filename: str) -> str:
    """Dosya adını güvenli hale getirir"""
    # Geçersiz karakterleri kaldır
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Boşlukları alt çizgi ile değiştir
    filename = filename.replace(' ', '_')
    
    # Maksimum uzunluk kontrolü
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def compress_image(image: np.ndarray, quality: int = 85) -> bytes:
    """Görüntüyü sıkıştırır"""
    try:
        encode_param = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success, img_encoded = cv2.imencode('.jpg', image, encode_param)
        
        if success:
            return img_encoded.tobytes()
        return b''
    except Exception:
        return b''

def get_local_ip_addresses() -> List[str]:
    """Tüm yerel IP adreslerini döndürür"""
    ip_addresses = []
    
    try:
        # Platform bağımsız yöntem
        hostname = socket.gethostname()
        ip_addresses.append(socket.gethostbyname(hostname))
        
        # Tüm network interface'leri kontrol et
        if hasattr(socket, 'AF_INET'):
            for interface in socket.getaddrinfo(hostname, None):
                ip = interface[4][0]
                if ip not in ip_addresses and not ip.startswith('127.'):
                    ip_addresses.append(ip)
    
    except Exception:
        pass
    
    # Fallback
    if not ip_addresses:
        ip_addresses.append('127.0.0.1')
    
    return ip_addresses

def bytes_to_human_readable(bytes_value: int) -> str:
    """Byte değerini okunabilir formata çevirir"""
    return format_file_size(bytes_value)

def human_readable_to_bytes(human_readable: str) -> int:
    """Okunabilir formatı byte'a çevirir"""
    try:
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        # Sayı ve birimi ayır
        import re
        match = re.match(r'([0-9.]+)\s*([A-Z]+)', human_readable.upper())
        
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            
            if unit in units:
                return int(value * units[unit])
        
        return 0
    except Exception:
        return 0

def get_cpu_usage() -> float:
    """CPU kullanım yüzdesini döndürür"""
    try:
        return psutil.cpu_percent(interval=1)
    except Exception:
        return 0.0

def get_memory_usage() -> Dict[str, float]:
    """Bellek kullanım bilgilerini döndürür"""
    try:
        memory = psutil.virtual_memory()
        return {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'percent': memory.percent
        }
    except Exception:
        return {}

def get_disk_usage(path: str = '/') -> Dict[str, float]:
    """Disk kullanım bilgilerini döndürür"""
    try:
        if os.name == 'nt':  # Windows
            path = 'C:\\'
        
        usage = shutil.disk_usage(path)
        return {
            'total_gb': round(usage.total / (1024**3), 2),
            'free_gb': round(usage.free / (1024**3), 2),
            'used_gb': round((usage.total - usage.free) / (1024**3), 2),
            'percent': round(((usage.total - usage.free) / usage.total) * 100, 1)
        }
    except Exception:
        return {}

# Global instances
_performance_monitor = PerformanceMonitor()
_data_cache = DataCache()

def get_performance_monitor() -> PerformanceMonitor:
    """Global performance monitor'ı döndürür"""
    return _performance_monitor

def get_data_cache() -> DataCache:
    """Global data cache'i döndürür"""
    return _data_cache

# Test fonksiyonu
def test_helpers():
    """Yardımcı fonksiyonları test eder"""
    print("=== SYSTEM INFO TEST ===")
    print(json.dumps(get_system_info(), indent=2))
    
    print("\n=== NETWORK INFO TEST ===")
    print(json.dumps(get_network_info(), indent=2))
    
    print("\n=== VALIDATION TESTS ===")
    print(f"Email validation: {validate_email('test@example.com')}")
    print(f"Phone validation: {validate_phone_number('+905551234567')}")
    print(f"URL validation: {validate_url('https://www.example.com')}")
    
    print("\n=== FORMAT TESTS ===")
    print(f"Duration: {format_duration(3661)}")
    print(f"File size: {format_file_size(1234567890)}")
    print(f"Datetime: {format_datetime(time.time())}")
    
    print("\n=== CAMERA TEST ===")
    cameras = get_available_cameras()
    print(f"Available cameras: {cameras}")
    
    if cameras:
        camera_test = test_camera(cameras[0])
        print(f"Camera 0 test: {camera_test}")
    
    print("\n=== PERFORMANCE TEST ===")
    monitor = get_performance_monitor()
    
    monitor.start_timer('test_operation')
    time.sleep(0.1)  # Simulate work
    duration = monitor.end_timer('test_operation')
    
    print(f"Test operation took: {duration:.3f}s")
    print(f"Stats: {monitor.get_stats('test_operation')}")
    
    print("\n=== CACHE TEST ===")
    cache = get_data_cache()
    
    cache.set('test_key', {'data': 'test_value'}, ttl=5)
    print(f"Cached value: {cache.get('test_key')}")
    
    print("\n=== SYSTEM RESOURCES ===")
    print(f"CPU Usage: {get_cpu_usage():.1f}%")
    print(f"Memory: {get_memory_usage()}")
    print(f"Disk: {get_disk_usage()}")

if __name__ == "__main__":
    test_helpers()