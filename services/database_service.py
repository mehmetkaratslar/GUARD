# =======================================================================================
# 📄 Dosya Adı   : database_service.py
# 📁 Konum       : guard_pc/services/database_service.py
# 📌 Açıklama    : Firestore tabanlı kullanıcı ve düşme olayı yönetimi
#                 - Kullanıcı kayıt/güncelleme/ayar işlemleri
#                 - Düşme olaylarını kaydetme, listeleme, silme
#                 - Firestore çalışmazsa tüm veriler yerel JSON dosyasına kaydedilir
#                 - Olay kaydı hem yeni hem eski koleksiyon yapısına otomatik uyum sağlar
#
# 🔗 Bağlantılı Dosyalar:
#   - config/firebase_config.py : Firebase bağlantısı
#   - config/settings.py        : Veritabanı ayarları
#   - services/auth_service.py  : Kullanıcı kimlik doğrulama
#   - services/notification_service.py : Olay sonrası bildirim tetikler
# =======================================================================================

import logging
import os
import json
import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config.firebase_config import get_firestore_client, is_firebase_connected
from config.settings import Settings

class DatabaseService:
    """Firestore veritabanı işlemlerini yöneten sınıf."""
    
    def __init__(self):
        """Veritabanı servisini başlatır"""
        self.db = get_firestore_client()
        self.is_available = is_firebase_connected()
        
        if not self.is_available:
            logging.warning("Firestore başlatılamadı, yerel dosya tabanlı veri saklama kullanılacak")
            self._memory_storage = {"users": {}}
            self._load_local_data()
        else:
            logging.info("Firestore bağlantısı başarılı")
    
    def _get_local_data_path(self):
        """Yerel veri dosyasının yolunu döndürür."""
        data_dir = Settings.LOCAL_DB_PATH
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "local_db.json")
    
    def _load_local_data(self):
        """Yerel veri dosyasından verileri yükler."""
        try:
            file_path = self._get_local_data_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._memory_storage = data
                    logging.info(f"Yerel veri dosyası yüklendi: {file_path}")
            else:
                logging.info("Yerel veri dosyası bulunamadı, yeni dosya oluşturulacak")
                self._save_local_data()
        except Exception as e:
            logging.error(f"Yerel veri yüklenirken hata: {str(e)}")
    
    def _save_local_data(self):
        """Verileri yerel dosyaya kaydeder."""
        try:
            file_path = self._get_local_data_path()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._memory_storage, f, indent=2, ensure_ascii=False)
            logging.debug(f"Veriler yerel dosyaya kaydedildi: {file_path}")
        except Exception as e:
            logging.error(f"Veriler yerel dosyaya kaydedilirken hata: {str(e)}")

    def get_user_data(self, user_id: str) -> Optional[Dict]:
        """Kullanıcı verilerini getirir."""
        if not self.is_available:
            user_data = self._memory_storage["users"].get(user_id, None)
            if user_data:
                logging.info(f"Yerel depodan kullanıcı verisi alındı: {user_id}")
            return user_data
        
        try:
            from google.cloud import firestore
            user_ref = self.db.collection("users").document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                logging.info(f"Firestore'dan kullanıcı verisi alındı: {user_id}")
                return user_doc.to_dict()
            else:
                logging.warning(f"Kullanıcı bulunamadı: {user_id}")
                return None
                
        except Exception as e:
            logging.error(f"Kullanıcı verileri getirilirken hata oluştu: {str(e)}")
            return None

    def save_user_settings(self, user_id: str, settings: Dict) -> bool:
        """Kullanıcı ayarlarını kaydeder."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            
            if "settings" not in self._memory_storage["users"][user_id]:
                self._memory_storage["users"][user_id]["settings"] = {}
            
            self._memory_storage["users"][user_id]["settings"].update(settings)
            self._memory_storage["users"][user_id]["updated_at"] = time.time()
            
            self._save_local_data()
            logging.info(f"Kullanıcı ayarları yerel depoya kaydedildi: {user_id}")
            return True
        
        try:
            from google.cloud import firestore
            user_ref = self.db.collection("users").document(user_id)
            
            settings["updated_at"] = firestore.SERVER_TIMESTAMP
            
            user_ref.set({"settings": settings}, merge=True)
            logging.info(f"Kullanıcı ayarları güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"Kullanıcı ayarları kaydedilirken hata oluştu: {str(e)}")
            return False
    
    def save_fall_event(self, user_id: str, event_data: Dict) -> bool:
        """Düşme olayını veritabanına kaydeder."""
        if "id" not in event_data:
            event_data["id"] = str(uuid.uuid4())
            
        if "user_id" not in event_data:
            event_data["user_id"] = user_id
            
        if "timestamp" not in event_data:
            event_data["timestamp"] = time.time()
        
        if "created_at" not in event_data:
            event_data["created_at"] = time.time()
            
        logging.info(f"Düşme olayı kaydediliyor: {event_data.get('id')} - Kullanıcı: {user_id}")
        
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            
            if "events" not in self._memory_storage["users"][user_id]:
                self._memory_storage["users"][user_id]["events"] = []
            
            self._memory_storage["users"][user_id]["events"].append(event_data)
            
            if "fall_events" not in self._memory_storage["users"][user_id]:
                self._memory_storage["users"][user_id]["fall_events"] = []
                
            self._memory_storage["users"][user_id]["fall_events"].append(event_data)
            
            self._save_local_data()
            logging.info(f"Düşme olayı yerel depoya kaydedildi: {event_data.get('id')}")
            return True
        
        try:
            from google.cloud import firestore
            
            # events koleksiyonuna kaydet (yeni kod için)
            events_ref = self.db.collection("users").document(user_id).collection("events")
            events_ref.document(event_data["id"]).set(event_data)
            
            # fall_events koleksiyonuna da kaydet (eski kod için)
            fall_events_ref = self.db.collection("users").document(user_id).collection("fall_events")
            fall_events_ref.document(event_data["id"]).set(event_data)
            
            logging.info(f"Düşme olayı veritabanına kaydedildi: {event_data.get('id')}")
            return True
            
        except Exception as e:
            logging.error(f"Düşme olayı kaydedilirken hata: {str(e)}", exc_info=True)
            return False

    def get_fall_events(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Kullanıcının düşme olaylarını getirir."""
        logging.info(f"Düşme olayları getiriliyor - Kullanıcı: {user_id}, Limit: {limit}")
        
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                logging.warning(f"Kullanıcı bellekte bulunamadı: {user_id}")
                return []
            
            events = self._memory_storage["users"][user_id].get("events", [])
            
            if not events:
                events = self._memory_storage["users"][user_id].get("fall_events", [])
            
            sorted_events = sorted(
                events, 
                key=lambda e: e.get("timestamp", e.get("created_at", 0)), 
                reverse=True
            )
            
            logging.info(f"Yerel depodan {len(sorted_events[:limit])} düşme olayı getirildi")
            return sorted_events[:limit]
            
        try:
            from google.cloud import firestore
            
            events_ref = self.db.collection("users").document(user_id).collection("events")
            query = events_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            
            events = []
            for doc in query.stream():
                event_data = doc.to_dict()
                if "id" not in event_data:
                    event_data["id"] = doc.id
                events.append(event_data)
            
            if not events:
                fall_events_ref = self.db.collection("users").document(user_id).collection("fall_events")
                query = fall_events_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
                
                for doc in query.stream():
                    event_data = doc.to_dict()
                    if "id" not in event_data:
                        event_data["id"] = doc.id
                    events.append(event_data)
            
            logging.info(f"Veritabanından {len(events)} düşme olayı getirildi")
            return events
            
        except Exception as e:
            logging.error(f"Düşme olayları getirilirken hata oluştu: {str(e)}")
            return []
    
    def create_new_user(self, user_id: str, user_data: Dict) -> bool:
        """Yeni kullanıcı oluşturur."""
        base_data = {
            "id": user_id,
            "created_at": time.time(),
            "last_login": time.time(),
            "settings": Settings.DEFAULT_NOTIFICATION_SETTINGS.copy()
        }
        
        user_data = {**base_data, **user_data}
        
        if not self.is_available:
            self._memory_storage["users"][user_id] = user_data
            self._save_local_data()
            logging.info(f"Yeni kullanıcı yerel depoya kaydedildi: {user_id}")
            return True
            
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.set(user_data)
            logging.info(f"Yeni kullanıcı oluşturuldu: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"Kullanıcı oluşturulurken hata oluştu: {str(e)}")
            return False
    
    def update_last_login(self, user_id: str) -> bool:
        """Kullanıcının son giriş zamanını günceller."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            
            self._memory_storage["users"][user_id]["last_login"] = time.time()
            self._save_local_data()
            logging.info(f"Son giriş zamanı yerel depoda güncellendi: {user_id}")
            return True
            
        try:
            from google.cloud import firestore
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update({"last_login": firestore.SERVER_TIMESTAMP})
            logging.info(f"Son giriş zamanı güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"Son giriş zamanı güncellenirken hata oluştu: {str(e)}")
            return False
    
    def update_user_data(self, user_id: str, user_data: Dict) -> bool:
        """Kullanıcı bilgilerini günceller."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                self._memory_storage["users"][user_id] = {"id": user_id}
            
            self._memory_storage["users"][user_id].update(user_data)
            self._memory_storage["users"][user_id]["updated_at"] = time.time()
            
            self._save_local_data()
            logging.info(f"Kullanıcı verileri yerel depoda güncellendi: {user_id}")
            return True
            
        try:
            from google.cloud import firestore
            user_ref = self.db.collection("users").document(user_id)
            
            user_data["updated_at"] = firestore.SERVER_TIMESTAMP
            
            user_ref.update(user_data)
            logging.info(f"Kullanıcı verileri güncellendi: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"Kullanıcı verileri güncellenirken hata oluştu: {str(e)}")
            return False
    
    def delete_fall_event(self, user_id: str, event_id: str) -> bool:
        """Düşme olayını siler."""
        if not self.is_available:
            if user_id not in self._memory_storage["users"]:
                return False
            
            for collection_name in ["events", "fall_events"]:
                if collection_name in self._memory_storage["users"][user_id]:
                    events = self._memory_storage["users"][user_id][collection_name]
                    self._memory_storage["users"][user_id][collection_name] = [
                        e for e in events if e.get("id") != event_id
                    ]
            
            self._save_local_data()
            logging.info(f"Düşme olayı yerel depodan silindi: {event_id}")
            return True
            
        try:
            events_ref = self.db.collection("users").document(user_id).collection("events").document(event_id)
            events_ref.delete()
            
            fall_events_ref = self.db.collection("users").document(user_id).collection("fall_events").document(event_id)
            fall_events_ref.delete()
            
            logging.info(f"Düşme olayı veritabanından silindi: {event_id}")
            return True
            
        except Exception as e:
            logging.error(f"Düşme olayı silinirken hata oluştu: {str(e)}")
            return False
    
    def cleanup_old_events(self, user_id: str) -> int:
        """Eski olayları temizler."""
        if not Settings.AUTO_DELETE_OLD_EVENTS:
            return 0
        
        try:
            cutoff_time = time.time() - (Settings.MAX_EVENT_STORAGE_DAYS * 24 * 60 * 60)
            deleted_count = 0
            
            if not self.is_available:
                if user_id in self._memory_storage["users"]:
                    for collection_name in ["events", "fall_events"]:
                        if collection_name in self._memory_storage["users"][user_id]:
                            events = self._memory_storage["users"][user_id][collection_name]
                            old_events = [e for e in events if e.get("timestamp", e.get("created_at", 0)) < cutoff_time]
                            deleted_count += len(old_events)
                            
                            self._memory_storage["users"][user_id][collection_name] = [
                                e for e in events if e.get("timestamp", e.get("created_at", 0)) >= cutoff_time
                            ]
                    
                    if deleted_count > 0:
                        self._save_local_data()
                        
                return deleted_count
            
            # Firestore'dan eski olayları sil
            from google.cloud import firestore
            
            for collection_name in ["events", "fall_events"]:
                collection_ref = self.db.collection("users").document(user_id).collection(collection_name)
                timestamp_field = "timestamp" if collection_name == "events" else "created_at"
                
                query = collection_ref.where(timestamp_field, "<", cutoff_time)
                
                docs = query.stream()
                for doc in docs:
                    doc.reference.delete()
                    deleted_count += 1
            
            if deleted_count > 0:
                logging.info(f"{deleted_count} eski olay temizlendi - Kullanıcı: {user_id}")
            
            return deleted_count
            
        except Exception as e:
            logging.error(f"Eski olaylar temizlenirken hata: {str(e)}")
            return 0
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Kullanıcı istatistiklerini döndürür."""
        try:
            events = self.get_fall_events(user_id, limit=1000)  # Son 1000 olay
            
            if not events:
                return {
                    "total_events": 0,
                    "events_today": 0,
                    "events_this_week": 0,
                    "events_this_month": 0,
                    "last_event": None
                }
            
            now = time.time()
            today_start = now - (now % 86400)  # Bugünün başlangıcı
            week_start = now - (7 * 86400)     # 7 gün önce
            month_start = now - (30 * 86400)   # 30 gün önce
            
            events_today = sum(1 for e in events if e.get("timestamp", e.get("created_at", 0)) >= today_start)
            events_this_week = sum(1 for e in events if e.get("timestamp", e.get("created_at", 0)) >= week_start)
            events_this_month = sum(1 for e in events if e.get("timestamp", e.get("created_at", 0)) >= month_start)
            
            return {
                "total_events": len(events),
                "events_today": events_today,
                "events_this_week": events_this_week,
                "events_this_month": events_this_month,
                "last_event": events[0] if events else None
            }
            
        except Exception as e:
            logging.error(f"Kullanıcı istatistikleri alınırken hata: {str(e)}")
            return {"total_events": 0, "events_today": 0, "events_this_week": 0, "events_this_month": 0, "last_event": None}

# Global database service instance'ı
_database_service_instance = None

def get_database_service() -> DatabaseService:
    """Global DatabaseService instance'ını döndürür"""
    global _database_service_instance
    if _database_service_instance is None:
        _database_service_instance = DatabaseService()
    return _database_service_instance