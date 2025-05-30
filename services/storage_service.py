# =======================================================================================
# 📄 Dosya Adı   : storage_service.py
# 📁 Konum       : guard_pc/services/storage_service.py
# 📌 Açıklama    : Firebase Storage işlemlerini yöneten sınıf
#                 - Düşme anında ekran görüntüsü yükleme/indirme
#                 - Firebase Storage çalışmazsa yerel dosya sistemi kullanır
#                 - Görüntü optimizasyonu ve metadata yönetimi
#
# 🔗 Bağlantılı Dosyalar:
#   - config/firebase_config.py : Firebase Storage bağlantısı
#   - config/settings.py        : Storage ayarları
#   - services/camera_service.py : Ekran görüntüsü yakalama
#   - services/database_service.py : Görüntü URL'sini veritabanına kaydetme
# =======================================================================================

import logging
import os
import uuid
import time
import cv2
import numpy as np
from typing import Optional, List
from datetime import timedelta

from config.firebase_config import get_storage_bucket, is_firebase_connected
from config.settings import Settings

class StorageService:
    """Firebase Storage işlemlerini yöneten sınıf."""
    
    def __init__(self):
        """Storage servisini başlatır"""
        self.bucket = get_storage_bucket()
        self.is_available = is_firebase_connected() and self.bucket is not None
        
        if not self.is_available:
            logging.warning("Firebase Storage başlatılamadı, yerel dosya depolama kullanılacak")
            self.local_storage_dir = os.path.join(Settings.LOCAL_DB_PATH, "screenshots")
            os.makedirs(self.local_storage_dir, exist_ok=True)
        else:
            logging.info("Firebase Storage bağlantısı başarılı")
    
    def upload_screenshot(self, user_id: str, image: np.ndarray, event_id: str = None) -> Optional[str]:
        """Ekran görüntüsünü Firebase Storage'a veya yerel depolamaya yükler.
        
        Args:
            user_id (str): Kullanıcı ID'si
            image (numpy.ndarray): Yüklenecek görüntü (OpenCV formatında)
            event_id (str, optional): Olay ID'si
            
        Returns:
            str: Yüklenen dosyanın URL'si/yolu, hata durumunda None
        """
        try:
            if event_id is None:
                event_id = str(uuid.uuid4())
                
            if image is None or image.size == 0:
                logging.error("Boş görüntü yüklenemez")
                return None
                
            logging.info(f"Ekran görüntüsü yükleniyor - User: {user_id}, Event: {event_id}")
            
            # Görüntüyü optimize et
            optimized_image = self._optimize_image(image)
            
            if not self.is_available:
                return self._upload_local(user_id, optimized_image, event_id)
            
            return self._upload_firebase(user_id, optimized_image, event_id)
                
        except Exception as e:
            logging.error(f"Ekran görüntüsü yüklenirken hata oluştu: {str(e)}", exc_info=True)
            return None
    
    def _optimize_image(self, image: np.ndarray) -> np.ndarray:
        """Görüntüyü optimize eder (boyut ve kalite)"""
        try:
            height, width = image.shape[:2]
            
            # Maksimum boyutları kontrol et
            max_width = 1280
            max_height = 720
            
            if width > max_width or height > max_height:
                # Oranı koruyarak yeniden boyutlandır
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logging.debug(f"Görüntü yeniden boyutlandırıldı: {width}x{height} -> {new_width}x{new_height}")
            
            return image
            
        except Exception as e:
            logging.error(f"Görüntü optimizasyonunda hata: {str(e)}")
            return image
    
    def _upload_local(self, user_id: str, image: np.ndarray, event_id: str) -> Optional[str]:
        """Yerel depolamaya kaydet."""
        try:
            user_dir = os.path.join(self.local_storage_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            local_path = os.path.join(user_dir, f"{event_id}.jpg")
            
            # OpenCV görüntüsünü JPEG olarak kaydet
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
            success = cv2.imwrite(local_path, image, encode_params)
            
            if success:
                logging.info(f"Ekran görüntüsü yerel depolamaya kaydedildi: {local_path}")
                return f"file://{os.path.abspath(local_path)}"
            else:
                logging.error("Görüntü yerel depolamaya kaydedilemedi")
                return None
                
        except Exception as e:
            logging.error(f"Yerel depolama hatası: {str(e)}")
            return None
    
    def _upload_firebase(self, user_id: str, image: np.ndarray, event_id: str) -> Optional[str]:
        """Firebase Storage'a yükle."""
        try:
            # Görüntüyü JPEG formatında byte dizisine dönüştür
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 85]
            success, img_encoded = cv2.imencode('.jpg', image, encode_param)
            
            if not success:
                logging.error("Görüntü encode edilemedi")
                return None
            
            img_bytes = img_encoded.tobytes()
            
            # Firebase Storage yolu
            destination_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(destination_path)
            
            # Metadata ekle
            blob.metadata = {
                'user_id': user_id,
                'event_id': event_id,
                'upload_time': str(int(time.time())),
                'content_type': 'image/jpeg',
                'file_size': str(len(img_bytes))
            }
            
            # Byte dizisinden yükle
            blob.upload_from_string(
                img_bytes,
                content_type='image/jpeg'
            )
            
            # Public URL oluştur
            try:
                # Access token oluştur
                access_token = str(uuid.uuid4())
                blob.metadata['firebaseStorageDownloadTokens'] = access_token
                blob.patch()
                
                # Public URL oluştur
                bucket_name = self.bucket.name
                public_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{destination_path.replace('/', '%2F')}?alt=media&token={access_token}"
                
                logging.info(f"Ekran görüntüsü Firebase Storage'a yüklendi: {destination_path}")
                return public_url
                
            except Exception as token_error:
                logging.warning(f"Access token oluşturulamadı: {str(token_error)}")
                # Signed URL oluştur
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=365),
                    method="GET"
                )
                logging.info(f"Signed URL oluşturuldu: {destination_path}")
                return url
            
        except Exception as e:
            logging.error(f"Firebase Storage yükleme hatası: {str(e)}")
            return None
    
    def get_screenshot_url(self, user_id: str, event_id: str) -> Optional[str]:
        """Ekran görüntüsünün URL'sini döndürür."""
        try:
            if not self.is_available:
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    return f"file://{os.path.abspath(local_path)}"
                else:
                    logging.warning(f"Görüntü bulunamadı: {local_path}")
                    return None
            
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                blob.reload()
                if blob.metadata and 'firebaseStorageDownloadTokens' in blob.metadata:
                    token = blob.metadata['firebaseStorageDownloadTokens']
                    bucket_name = self.bucket.name
                    return f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{blob_path.replace('/', '%2F')}?alt=media&token={token}"
                else:
                    url = blob.generate_signed_url(
                        version="v4",
                        expiration=timedelta(days=365),
                        method="GET"
                    )
                    return url
            else:
                logging.warning(f"Görüntü bulunamadı: {blob_path}")
                return None
                
        except Exception as e:
            logging.error(f"Görüntü URL'si alınırken hata oluştu: {str(e)}")
            return None
    
    def download_screenshot(self, user_id: str, event_id: str) -> Optional[np.ndarray]:
        """Ekran görüntüsünü indirir ve numpy dizisi olarak döndürür."""
        try:
            if not self.is_available:
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    img = cv2.imread(local_path)
                    return img
                else:
                    logging.warning(f"İndirilecek görüntü bulunamadı: {local_path}")
                    return None
            
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                img_bytes = blob.download_as_bytes()
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return img
            else:
                logging.warning(f"İndirilecek görüntü bulunamadı: {blob_path}")
                return None
                
        except Exception as e:
            logging.error(f"Görüntü indirilirken hata oluştu: {str(e)}")
            return None
    
    def delete_screenshot(self, user_id: str, event_id: str) -> bool:
        """Ekran görüntüsünü Firebase Storage'dan veya yerel depolamadan siler."""
        try:
            if not self.is_available:
                local_path = os.path.join(self.local_storage_dir, user_id, f"{event_id}.jpg")
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logging.info(f"Ekran görüntüsü yerel depolamadan silindi: {local_path}")
                    return True
                else:
                    logging.warning(f"Silinecek ekran görüntüsü bulunamadı: {local_path}")
                    return False
            
            blob_path = f"fall_events/{user_id}/{event_id}.jpg"
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                blob.delete()
                logging.info(f"Ekran görüntüsü silindi: {blob_path}")
                return True
            else:
                logging.warning(f"Silinecek ekran görüntüsü bulunamadı: {blob_path}")
                return False
                
        except Exception as e:
            logging.error(f"Ekran görüntüsü silinirken hata oluştu: {str(e)}")
            return False
    
    def list_all_screenshots(self, user_id: str) -> List[str]:
        """Kullanıcının tüm ekran görüntülerini listeler."""
        try:
            if not self.is_available:
                user_dir = os.path.join(self.local_storage_dir, user_id)
                if not os.path.exists(user_dir):
                    return []
                
                files = os.listdir(user_dir)
                event_ids = [f.replace('.jpg', '') for f in files if f.endswith('.jpg')]
                return event_ids
            
            prefix = f"fall_events/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            event_ids = []
            for blob in blobs:
                filename = os.path.basename(blob.name)
                if filename.endswith('.jpg'):
                    event_id = filename.replace('.jpg', '')
                    event_ids.append(event_id)
            
            return event_ids
                
        except Exception as e:
            logging.error(f"Ekran görüntüleri listelenirken hata oluştu: {str(e)}")
            return []
    
    def cleanup_old_screenshots(self, user_id: str, days_old: int = 30) -> int:
        """Eski ekran görüntülerini temizler."""
        try:
            deleted_count = 0
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            
            if not self.is_available:
                user_dir = os.path.join(self.local_storage_dir, user_id)
                if not os.path.exists(user_dir):
                    return 0
                
                for filename in os.listdir(user_dir):
                    if filename.endswith('.jpg'):
                        file_path = os.path.join(user_dir, filename)
                        file_time = os.path.getctime(file_path)
                        
                        if file_time < cutoff_time:
                            os.remove(file_path)
                            deleted_count += 1
                            logging.debug(f"Eski görüntü silindi: {filename}")
                
                return deleted_count
            
            # Firebase Storage'dan eski dosyaları sil
            prefix = f"fall_events/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            for blob in blobs:
                try:
                    blob.reload()
                    
                    # Blob'un oluşturulma zamanını kontrol et
                    if blob.time_created:
                        blob_time = blob.time_created.timestamp()
                        
                        if blob_time < cutoff_time:
                            blob.delete()
                            deleted_count += 1
                            logging.debug(f"Eski görüntü silindi: {blob.name}")
                            
                except Exception as blob_error:
                    logging.warning(f"Blob işlenirken hata: {str(blob_error)}")
                    continue
            
            if deleted_count > 0:
                logging.info(f"{deleted_count} eski ekran görüntüsü temizlendi - Kullanıcı: {user_id}")
            
            return deleted_count
            
        except Exception as e:
            logging.error(f"Eski görüntüler temizlenirken hata: {str(e)}")
            return 0
    
    def get_storage_stats(self, user_id: str) -> dict:
        """Kullanıcının depolama istatistiklerini döndürür."""
        try:
            stats = {
                "total_screenshots": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "oldest_screenshot": None,
                "newest_screenshot": None
            }
            
            if not self.is_available:
                user_dir = os.path.join(self.local_storage_dir, user_id)
                if not os.path.exists(user_dir):
                    return stats
                
                files = [f for f in os.listdir(user_dir) if f.endswith('.jpg')]
                stats["total_screenshots"] = len(files)
                
                oldest_time = None
                newest_time = None
                
                for filename in files:
                    file_path = os.path.join(user_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_time = os.path.getctime(file_path)
                    
                    stats["total_size_bytes"] += file_size
                    
                    if oldest_time is None or file_time < oldest_time:
                        oldest_time = file_time
                        stats["oldest_screenshot"] = filename.replace('.jpg', '')
                    
                    if newest_time is None or file_time > newest_time:
                        newest_time = file_time
                        stats["newest_screenshot"] = filename.replace('.jpg', '')
                
                stats["total_size_mb"] = stats["total_size_bytes"] / (1024 * 1024)
                return stats
            
            # Firebase Storage istatistikleri
            prefix = f"fall_events/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            oldest_time = None
            newest_time = None
            
            for blob in blobs:
                if blob.name.endswith('.jpg'):
                    stats["total_screenshots"] += 1
                    
                    try:
                        blob.reload()
                        if blob.size:
                            stats["total_size_bytes"] += blob.size
                        
                        if blob.time_created:
                            blob_time = blob.time_created.timestamp()
                            
                            if oldest_time is None or blob_time < oldest_time:
                                oldest_time = blob_time
                                stats["oldest_screenshot"] = os.path.basename(blob.name).replace('.jpg', '')
                            
                            if newest_time is None or blob_time > newest_time:
                                newest_time = blob_time
                                stats["newest_screenshot"] = os.path.basename(blob.name).replace('.jpg', '')
                                
                    except Exception as blob_error:
                        logging.warning(f"Blob bilgileri alınırken hata: {str(blob_error)}")
                        continue
            
            stats["total_size_mb"] = stats["total_size_bytes"] / (1024 * 1024)
            return stats
            
        except Exception as e:
            logging.error(f"Depolama istatistikleri alınırken hata: {str(e)}")
            return {"total_screenshots": 0, "total_size_bytes": 0, "total_size_mb": 0.0}

# Global storage service instance'ı
_storage_service_instance = None

def get_storage_service() -> StorageService:
    """Global StorageService instance'ını döndürür"""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance