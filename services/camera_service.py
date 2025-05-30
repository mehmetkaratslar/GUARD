# =======================================================================================
# 📄 Dosya Adı   : camera_service.py
# 📁 Konum       : guard_pc/services/camera_service.py
# 📌 Açıklama    : Kamera görüntü yakalama ve düşme tespit sistemi
#                 - Kamera bağlantısı ve görüntü yakalama
#                 - Gerçek zamanlı düşme tespiti
#                 - Tespit sonrası otomatik bildirim ve kayıt
#
# 🔗 Bağlantılı Dosyalar:
#   - models/fall_detector.py   : Düşme tespit modeli
#   - services/database_service.py : Olay kaydetme
#   - services/storage_service.py  : Ekran görüntüsü kaydetme
#   - services/notification_service.py : Bildirim gönderme
#   - config/settings.py        : Kamera ayarları
# =======================================================================================

import logging
import cv2
import numpy as np
import time
import threading
from typing import Optional, Callable, Dict, Tuple
from datetime import datetime

from config.settings import Settings
from models.fall_detector import get_fall_detector
from services.database_service import get_database_service
from services.storage_service import get_storage_service

class CameraService:
    """Kamera ve görüntü işleme servisi"""
    
    def __init__(self, user_id: str = None):
        """
        Args:
            user_id (str): Mevcut kullanıcının ID'si
        """
        self.user_id = user_id
        self.camera = None
        self.is_running = False
        self.is_detecting = False
        
        # Kamera ayarları
        self.camera_index = Settings.CAMERA_INDEX
        self.camera_width = Settings.CAMERA_WIDTH
        self.camera_height = Settings.CAMERA_HEIGHT
        self.camera_fps = Settings.CAMERA_FPS
        
        # Görüntü işleme
        self.current_frame = None
        self.processed_frame = None
        self.frame_lock = threading.Lock()
        
        # Tespit sistemi
        self.fall_detector = get_fall_detector()
        self.database_service = get_database_service()
        self.storage_service = get_storage_service()
        
        # Callback fonksiyonları
        self.frame_callback = None
        self.detection_callback = None
        self.error_callback = None
        
        # Performans takibi
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
        # Thread kontrol
        self.capture_thread = None
        self.processing_thread = None
        
        logging.info("CameraService başlatıldı")
    
    def set_user_id(self, user_id: str):
        """Kullanıcı ID'sini ayarlar"""
        self.user_id = user_id
        logging.info(f"Kullanıcı ID ayarlandı: {user_id}")
    
    def set_callbacks(self, frame_callback: Callable = None, 
                     detection_callback: Callable = None,
                     error_callback: Callable = None):
        """Callback fonksiyonlarını ayarlar"""
        self.frame_callback = frame_callback
        self.detection_callback = detection_callback
        self.error_callback = error_callback
        logging.info("Callback fonksiyonları ayarlandı")
    
    def initialize_camera(self) -> bool:
        """Kamerayı başlatır"""
        try:
            if self.camera is not None:
                self.release_camera()
            
            logging.info(f"Kamera başlatılıyor - Index: {self.camera_index}")
            
            # Kamerayı aç
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                logging.error(f"Kamera açılamadı - Index: {self.camera_index}")
                return False
            
            # Kamera ayarlarını yapılandır
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.camera_fps)
            
            # Buffer boyutunu azalt (düşük gecikme için)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test frame'i al
            ret, test_frame = self.camera.read()
            if not ret or test_frame is None:
                logging.error("Test frame'i alınamadı")
                return False
            
            # Gerçek ayarları al
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            logging.info(f"Kamera başarıyla açıldı - Çözünürlük: {actual_width}x{actual_height}, FPS: {actual_fps}")
            return True
            
        except Exception as e:
            logging.error(f"Kamera başlatılırken hata: {str(e)}")
            if self.error_callback:
                self.error_callback(f"Kamera hatası: {str(e)}")
            return False
    
    def start_capture(self) -> bool:
        """Görüntü yakalamayı başlatır"""
        try:
            if self.is_running:
                logging.warning("Görüntü yakalama zaten çalışıyor")
                return True
            
            if not self.fall_detector.is_loaded:
                logging.info("Fall detector yükleniyor...")
                if not self.fall_detector.load_model():
                    logging.error("Fall detector yüklenemedi")
                    return False
            
            if self.camera is None:
                if not self.initialize_camera():
                    return False
            
            self.is_running = True
            
            # Görüntü yakalama thread'ini başlat
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            # Görüntü işleme thread'ini başlat
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
            
            logging.info("Görüntü yakalama başlatıldı")
            return True
            
        except Exception as e:
            logging.error(f"Görüntü yakalama başlatılırken hata: {str(e)}")
            return False
    
    def stop_capture(self):
        """Görüntü yakalamayı durdurur"""
        try:
            if not self.is_running:
                return
            
            logging.info("Görüntü yakalama durduruluyor...")
            self.is_running = False
            
            # Thread'lerin bitmesini bekle
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=2.0)
            
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)
            
            logging.info("Görüntü yakalama durduruldu")
            
        except Exception as e:
            logging.error(f"Görüntü yakalama durdurulurken hata: {str(e)}")
    
    def _capture_loop(self):
        """Görüntü yakalama döngüsü (ayrı thread'de çalışır)"""
        try:
            while self.is_running and self.camera is not None:
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    logging.warning("Frame alınamadı")
                    time.sleep(0.1)
                    continue
                
                # Frame'i güvenli şekilde kaydet
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
                # FPS hesapla
                self._update_fps()
                
                # Frame callback'ini çağır
                if self.frame_callback:
                    try:
                        self.frame_callback(frame.copy())
                    except Exception as callback_error:
                        logging.error(f"Frame callback hatası: {str(callback_error)}")
                
                # CPU kullanımını azaltmak için kısa bekle
                time.sleep(Settings.DETECTION_INTERVAL)
                
        except Exception as e:
            logging.error(f"Capture loop hatası: {str(e)}")
            if self.error_callback:
                self.error_callback(f"Kamera hatası: {str(e)}")
    
    def _processing_loop(self):
        """Görüntü işleme döngüsü (ayrı thread'de çalışır)"""
        try:
            while self.is_running:
                # Mevcut frame'i al
                with self.frame_lock:
                    if self.current_frame is None:
                        time.sleep(0.1)
                        continue
                    
                    frame_to_process = self.current_frame.copy()
                
                # Düşme tespiti yap
                if self.is_detecting and self.user_id:
                    detection_result = self.fall_detector.detect_fall(frame_to_process)
                    
                    # Tespit sonuçlarını görüntü üzerine çiz
                    self.processed_frame = self.fall_detector.draw_detections(frame_to_process, detection_result)
                    
                    # Düşme tespit edildiyse
                    if detection_result["fall_detected"]:
                        self._handle_fall_detection(frame_to_process, detection_result)
                    
                    # Detection callback'ini çağır
                    if self.detection_callback:
                        try:
                            self.detection_callback(detection_result, self.processed_frame)
                        except Exception as callback_error:
                            logging.error(f"Detection callback hatası: {str(callback_error)}")
                else:
                    self.processed_frame = frame_to_process
                
                time.sleep(Settings.DETECTION_INTERVAL)
                
        except Exception as e:
            logging.error(f"Processing loop hatası: {str(e)}")
    
    def _handle_fall_detection(self, frame: np.ndarray, detection_result: Dict):
        """Düşme tespiti sonrası işlemleri yapar"""
        try:
            event_id = str(int(time.time() * 1000))  # Unique event ID
            
            logging.warning(f"DÜŞME TESPİT EDİLDİ! - Event ID: {event_id}, Güven: {detection_result['confidence']:.2f}")
            
            # Ekran görüntüsünü kaydet
            screenshot_url = self.storage_service.upload_screenshot(
                user_id=self.user_id,
                image=frame,
                event_id=event_id
            )
            
            # Olay verisini hazırla
            event_data = {
                "id": event_id,
                "user_id": self.user_id,
                "timestamp": time.time(),
                "created_at": time.time(),
                "confidence": detection_result["confidence"],
                "detection_count": detection_result["detection_count"],
                "detections": detection_result["detections"],
                "screenshot_url": screenshot_url,
                "location": "PC Kamerası",  # Sabit konum
                "status": "detected",
                "processed": False
            }
            
            # Veritabanına kaydet
            success = self.database_service.save_fall_event(self.user_id, event_data)
            
            if success:
                logging.info(f"Düşme olayı kaydedildi - Event ID: {event_id}")
                
                # Bildirim gönder (ayrı thread'de)
                threading.Thread(
                    target=self._send_notifications,
                    args=(event_data,),
                    daemon=True
                ).start()
            else:
                logging.error("Düşme olayı kaydedilemedi")
                
        except Exception as e:
            logging.error(f"Düşme tespiti işlenirken hata: {str(e)}")
    
    def _send_notifications(self, event_data: Dict):
        """Bildirimleri gönderir (ayrı thread'de çalışır)"""
        try:
            # Notification service import burada yapıyoruz (circular import önlemek için)
            from services.notification_service import get_notification_service
            
            notification_service = get_notification_service()
            notification_service.send_fall_alert(self.user_id, event_data)
            
        except Exception as e:
            logging.error(f"Bildirim gönderilirken hata: {str(e)}")
    
    def _update_fps(self):
        """FPS hesaplar"""
        self.fps_counter += 1
        
        if self.fps_counter >= 30:  # Her 30 frame'de bir hesapla
            current_time = time.time()
            elapsed_time = current_time - self.fps_start_time
            
            if elapsed_time > 0:
                self.current_fps = self.fps_counter / elapsed_time
            
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def start_detection(self):
        """Düşme tespitini başlatır"""
        if not self.user_id:
            logging.error("Düşme tespiti için kullanıcı ID gerekli")
            return False
        
        if not self.fall_detector.is_loaded:
            logging.error("Fall detector yüklenmemiş")
            return False
        
        self.is_detecting = True
        logging.info("Düşme tespiti başlatıldı")
        return True
    
    def stop_detection(self):
        """Düşme tespitini durdurur"""
        self.is_detecting = False
        logging.info("Düşme tespiti durduruldu")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Mevcut frame'i döndürür"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_processed_frame(self) -> Optional[np.ndarray]:
        """İşlenmiş frame'i döndürür"""
        return self.processed_frame.copy() if self.processed_frame is not None else None
    
    def capture_screenshot(self) -> Optional[np.ndarray]:
        """Manuel ekran görüntüsü alır"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def get_camera_info(self) -> Dict:
        """Kamera bilgilerini döndürür"""
        if self.camera is None:
            return {"status": "disconnected"}
        
        try:
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            return {
                "status": "connected" if self.is_running else "stopped",
                "width": width,
                "height": height,
                "fps": fps,
                "current_fps": self.current_fps,
                "is_detecting": self.is_detecting
            }
            
        except Exception as e:
            logging.error(f"Kamera bilgileri alınırken hata: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def release_camera(self):
        """Kamerayı serbest bırakır"""
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
                logging.info("Kamera serbest bırakıldı")
        except Exception as e:
            logging.error(f"Kamera serbest bırakılırken hata: {str(e)}")
    
    def cleanup(self):
        """Tüm kaynakları temizler"""
        try:
            self.stop_capture()
            self.release_camera()
            
            # Fall detector'ı temizle
            if self.fall_detector:
                self.fall_detector.cleanup()
            
            logging.info("CameraService temizlendi")
            
        except Exception as e:
            logging.error(f"Cleanup sırasında hata: {str(e)}")

# Global camera service instance'ı
_camera_service_instance = None

def get_camera_service() -> CameraService:
    """Global CameraService instance'ını döndürür"""
    global _camera_service_instance
    if _camera_service_instance is None:
        _camera_service_instance = CameraService()
    return _camera_service_instance

def initialize_camera_service(user_id: str) -> CameraService:
    """Kamera servisini kullanıcı ID'si ile başlatır"""
    camera_service = get_camera_service()
    camera_service.set_user_id(user_id)
    return camera_service