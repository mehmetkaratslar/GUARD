# =======================================================================================
# 📄 Dosya Adı   : fall_detector.py
# 📁 Konum       : guard_pc/models/fall_detector.py
# 📌 Açıklama    : YOLOv11 tabanlı düşme tespit modeli entegrasyonu
#                 - Eğitilmiş fall_model.pt modelini yükler ve çalıştırır
#                 - Görüntü ön işleme ve tahmin işlemleri
#                 - GPU/CPU otomatik seçimi ve performans optimizasyonu
#
# 🔗 Bağlantılı Dosyalar:
#   - models/fall_model.pt      : Eğitilmiş YOLOv11 modeli (buraya kopyalayın)
#   - config/settings.py        : Model yapılandırma ayarları
#   - services/camera_service.py : Kamera görüntülerini bu modele gönderir
# =======================================================================================

import os
import logging
import torch
import cv2
import numpy as np
from ultralytics import YOLO
import time
from typing import Tuple, List, Optional, Dict
from config.settings import Settings

class FallDetector:
    """YOLOv11 tabanlı düşme tespit sınıfı"""
    
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path (str, optional): Model dosyası yolu. None ise settings'den alır.
        """
        self.model_path = model_path or Settings.MODEL_PATH
        self.confidence_threshold = Settings.CONFIDENCE_THRESHOLD
        self.device = self._select_device()
        self.model = None
        self.is_loaded = False
        
        # Performans takibi
        self.inference_times = []
        self.detection_count = 0
        
        # Son tespit bilgileri (duplikasyon önleme için)
        self.last_detection_time = 0
        self.detection_cooldown = Settings.FALL_DETECTION_COOLDOWN
        
        logging.info(f"FallDetector başlatıldı - Device: {self.device}")
        
    def _select_device(self) -> str:
        """En uygun cihazı (GPU/CPU) seçer"""
        try:
            if Settings.GPU_ACCELERATION and torch.cuda.is_available():
                device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                logging.info(f"GPU kullanılacak: {gpu_name}")
            else:
                device = "cpu"
                logging.info("CPU kullanılacak")
            
            return device
            
        except Exception as e:
            logging.warning(f"Cihaz seçiminde hata: {str(e)}")
            return "cpu"
    
    def load_model(self) -> bool:
        """Modeli yükler"""
        try:
            # Model dosyasının varlığını kontrol et
            if not os.path.exists(self.model_path):
                logging.error(f"Model dosyası bulunamadı: {self.model_path}")
                logging.info("Model dosyasını şu konuma kopyalayın: models/fall_model.pt")
                return False
            
            logging.info(f"Model yükleniyor: {self.model_path}")
            
            # YOLOv11 modelini yükle
            self.model = YOLO(self.model_path)
            
            # Modeli seçilen cihaza taşı
            if self.device == "cuda":
                self.model.model = self.model.model.cuda()
            
            # Model bilgilerini al
            model_info = self.model.info()
            logging.info(f"Model başarıyla yüklendi - Classes: {len(self.model.names)}")
            logging.info(f"Model sınıfları: {self.model.names}")
            
            # Test tahmini yap (model doğrulaması için)
            test_image = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.model(test_image, verbose=False)
            logging.info("Model test tahmini başarılı")
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            logging.error(f"Model yüklenirken hata oluştu: {str(e)}")
            self.is_loaded = False
            return False
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Görüntüyü model için ön işleme tabi tutar"""
        try:
            # Görüntü boyutunu kontrol et
            if image is None or image.size == 0:
                logging.warning("Boş görüntü alındı")
                return None
            
            # BGR'den RGB'ye çevir (YOLO RGB bekler)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            return image_rgb
            
        except Exception as e:
            logging.error(f"Görüntü ön işlemede hata: {str(e)}")
            return None
    
    def detect_fall(self, image: np.ndarray) -> Dict:
        """Görüntüde düşme tespiti yapar"""
        if not self.is_loaded:
            logging.warning("Model yüklenmemiş, tespit yapılamıyor")
            return self._create_empty_result()
        
        try:
            start_time = time.time()
            
            # Görüntüyü ön işleme tabi tut
            processed_image = self.preprocess_image(image)
            if processed_image is None:
                return self._create_empty_result()
            
            # Model tahmini yap
            results = self.model(
                processed_image,
                conf=self.confidence_threshold,
                verbose=False,
                device=self.device
            )
            
            # Sonuçları işle
            detection_result = self._process_results(results[0], image.shape)
            
            # Performans bilgilerini güncelle
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            if len(self.inference_times) > 100:  # Son 100 tahmini sakla
                self.inference_times.pop(0)
            
            # Tespit sayısını artır
            if detection_result["fall_detected"]:
                self.detection_count += 1
                self.last_detection_time = time.time()
            
            detection_result["inference_time"] = inference_time
            detection_result["avg_inference_time"] = np.mean(self.inference_times)
            
            return detection_result
            
        except Exception as e:
            logging.error(f"Düşme tespitinde hata: {str(e)}")
            return self._create_empty_result()
    
    def _process_results(self, result, image_shape: Tuple[int, int, int]) -> Dict:
        """YOLO sonuçlarını işler ve düşme tespiti yapar"""
        try:
            detections = []
            fall_detected = False
            max_confidence = 0.0
            
            # Tespit edilen nesneleri kontrol et
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    # Sınıf ID'sini al
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # Koordinatları al (x1, y1, x2, y2)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Sınıf adını al
                    class_name = self.model.names[class_id]
                    
                    detection_info = {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                    }
                    
                    detections.append(detection_info)
                    
                    # Düşme sınıfını kontrol et (varsayılan olarak 'fall' veya sınıf ID 0)
                    if self._is_fall_class(class_name, class_id):
                        fall_detected = True
                        max_confidence = max(max_confidence, confidence)
            
            # Cooldown kontrolü yap
            current_time = time.time()
            if fall_detected and (current_time - self.last_detection_time) < self.detection_cooldown:
                logging.info("Düşme tespiti cooldown'da, tespit atlandı")
                fall_detected = False
            
            return {
                "fall_detected": fall_detected,
                "confidence": max_confidence,
                "detections": detections,
                "detection_count": len(detections),
                "timestamp": current_time,
                "image_shape": image_shape
            }
            
        except Exception as e:
            logging.error(f"Sonuç işlemede hata: {str(e)}")
            return self._create_empty_result()
    
    def _is_fall_class(self, class_name: str, class_id: int) -> bool:
        """Sınıfın düşme sınıfı olup olmadığını kontrol eder"""
        # Düşme ile ilgili sınıf isimleri
        fall_classes = ["fall", "falling", "fallen", "person_fallen", "düşme"]
        
        # Sınıf ismini kontrol et
        if class_name.lower() in fall_classes:
            return True
        
        # Varsayılan olarak sınıf ID 0'ı düşme olarak kabul et
        if class_id == 0:
            return True
        
        return False
    
    def _create_empty_result(self) -> Dict:
        """Boş tespit sonucu oluşturur"""
        return {
            "fall_detected": False,
            "confidence": 0.0,
            "detections": [],
            "detection_count": 0,
            "timestamp": time.time(),
            "image_shape": None,
            "inference_time": 0.0,
            "avg_inference_time": 0.0
        }
    
    def draw_detections(self, image: np.ndarray, detection_result: Dict) -> np.ndarray:
        """Tespit sonuçlarını görüntü üzerine çizer"""
        try:
            if not detection_result["detections"]:
                return image
            
            result_image = image.copy()
            
            for detection in detection_result["detections"]:
                # Bounding box koordinatları
                x1, y1, x2, y2 = detection["bbox"]
                confidence = detection["confidence"]
                class_name = detection["class_name"]
                
                # Düşme tespiti ise kırmızı, diğerleri yeşil
                color = (0, 0, 255) if self._is_fall_class(class_name, detection["class_id"]) else (0, 255, 0)
                thickness = 3 if detection_result["fall_detected"] else 2
                
                # Bounding box çiz
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
                
                # Etiket metni
                label = f"{class_name}: {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                
                # Etiket arka planı
                cv2.rectangle(result_image, 
                            (x1, y1 - label_size[1] - 10), 
                            (x1 + label_size[0] + 10, y1), 
                            color, -1)
                
                # Etiket metni
                cv2.putText(result_image, label, 
                          (x1 + 5, y1 - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                          (255, 255, 255), 2)
            
            # Genel durum bilgisi
            status_text = "DÜŞME TESPİT EDİLDİ!" if detection_result["fall_detected"] else "Normal"
            status_color = (0, 0, 255) if detection_result["fall_detected"] else (0, 255, 0)
            
            cv2.putText(result_image, status_text,
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                       status_color, 2)
            
            # FPS bilgisi
            if detection_result.get("inference_time", 0) > 0:
                fps = 1.0 / detection_result["inference_time"]
                fps_text = f"FPS: {fps:.1f}"
                cv2.putText(result_image, fps_text,
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                           (255, 255, 255), 2)
            
            return result_image
            
        except Exception as e:
            logging.error(f"Tespit çiziminde hata: {str(e)}")
            return image
    
    def get_model_stats(self) -> Dict:
        """Model istatistiklerini döndürür"""
        return {
            "is_loaded": self.is_loaded,
            "model_path": self.model_path,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "detection_count": self.detection_count,
            "avg_inference_time": np.mean(self.inference_times) if self.inference_times else 0.0,
            "last_detection_time": self.last_detection_time,
            "model_classes": self.model.names if self.is_loaded else None
        }
    
    def update_confidence_threshold(self, new_threshold: float):
        """Güven eşiğini günceller"""
        if 0.0 <= new_threshold <= 1.0:
            self.confidence_threshold = new_threshold
            logging.info(f"Güven eşiği güncellendi: {new_threshold}")
        else:
            logging.warning(f"Geçersiz güven eşiği: {new_threshold}")
    
    def reset_stats(self):
        """İstatistikleri sıfırlar"""
        self.inference_times = []
        self.detection_count = 0
        self.last_detection_time = 0
        logging.info("Model istatistikleri sıfırlandı")
    
    def cleanup(self):
        """Kaynakları temizler"""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.is_loaded = False
            logging.info("FallDetector kaynakları temizlendi")
            
        except Exception as e:
            logging.error(f"Kaynak temizlemede hata: {str(e)}")

# Global model instance'ı (singleton pattern)
_fall_detector_instance = None

def get_fall_detector() -> FallDetector:
    """Global FallDetector instance'ını döndürür"""
    global _fall_detector_instance
    if _fall_detector_instance is None:
        _fall_detector_instance = FallDetector()
    return _fall_detector_instance

def initialize_fall_detector() -> bool:
    """Fall detector'ı başlatır"""
    detector = get_fall_detector()
    return detector.load_model()