# =======================================================================================
# 📄 Dosya Adı   : notification_service.py
# 📁 Konum       : guard_pc/services/notification_service.py
# 📌 Açıklama    : Çoklu kanal bildirim servisi
#                 - E-posta (SMTP/Gmail)
#                 - SMS (Twilio)
#                 - Telegram Bot
#                 - Desktop bildirimleri
#                 - Ses uyarıları
#
# 🔗 Bağlantılı Dosyalar:
#   - config/settings.py        : SMTP, Twilio, Telegram ayarları
#   - services/database_service.py : Kullanıcı bildirim tercihleri
#   - services/camera_service.py   : Düşme tespiti sonrası bildirim tetikleme
# =======================================================================================

import logging
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Dict, List, Optional
import requests
import json
import os
from datetime import datetime

from config.settings import Settings
from services.database_service import get_database_service

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    logging.warning("Twilio kütüphanesi bulunamadı, SMS desteği devre dışı")
    TWILIO_AVAILABLE = False

try:
    from plyer import notification as desktop_notification
    DESKTOP_NOTIFICATION_AVAILABLE = True
except ImportError:
    logging.warning("Plyer kütüphanesi bulunamadı, desktop bildirim desteği devre dışı")
    DESKTOP_NOTIFICATION_AVAILABLE = False

try:
    import pygame
    SOUND_AVAILABLE = True
except ImportError:
    logging.warning("Pygame kütüphanesi bulunamadı, ses desteği devre dışı")
    SOUND_AVAILABLE = False

class NotificationService:
    """Çoklu kanal bildirim servisi"""
    
    def __init__(self):
        """Bildirim servisini başlatır"""
        self.database_service = get_database_service()
        
        # SMTP ayarları
        self.smtp_host = Settings.SMTP_HOST
        self.smtp_port = Settings.SMTP_PORT
        self.smtp_user = Settings.SMTP_USER
        self.smtp_pass = Settings.SMTP_PASS
        
        # Twilio ayarları
        self.twilio_client = None
        if TWILIO_AVAILABLE and Settings.TWILIO_SID and Settings.TWILIO_TOKEN:
            try:
                self.twilio_client = TwilioClient(Settings.TWILIO_SID, Settings.TWILIO_TOKEN)
                logging.info("Twilio client başlatıldı")
            except Exception as e:
                logging.error(f"Twilio client başlatılamadı: {str(e)}")
        
        # Telegram ayarları
        self.telegram_token = Settings.TELEGRAM_BOT_TOKEN
        
        # Ses sistemi
        if SOUND_AVAILABLE:
            try:
                pygame.mixer.init()
                logging.info("Ses sistemi başlatıldı")
            except Exception as e:
                logging.error(f"Ses sistemi başlatılamadı: {str(e)}")
        
        # Son bildirim zamanları (spam önleme)
        self.last_notification_times = {}
        self.notification_cooldown = 60  # Saniye
        
        logging.info("NotificationService başlatıldı")
    
    def send_fall_alert(self, user_id: str, event_data: Dict):
        """Düşme uyarısı gönderir"""
        try:
            # Kullanıcı bildirim tercihlerini al
            user_data = self.database_service.get_user_data(user_id)
            if not user_data or "settings" not in user_data:
                logging.warning(f"Kullanıcı bildirim ayarları bulunamadı: {user_id}")
                return
            
            settings = user_data["settings"]
            
            # Cooldown kontrolü
            if not self._check_cooldown(user_id):
                logging.info("Bildirim cooldown'da, atlandı")
                return
            
            # Bildirim mesajını hazırla
            alert_message = self._prepare_alert_message(event_data)
            
            # Paralel olarak tüm bildirimleri gönder
            notification_threads = []
            
            # E-posta bildirimi
            if settings.get("email_notification", True) and user_data.get("email"):
                thread = threading.Thread(
                    target=self._send_email_alert,
                    args=(user_data["email"], alert_message, event_data),
                    daemon=True
                )
                notification_threads.append(thread)
            
            # SMS bildirimi
            if settings.get("sms_notification", False) and settings.get("phone_number"):
                thread = threading.Thread(
                    target=self._send_sms_alert,
                    args=(settings["phone_number"], alert_message),
                    daemon=True
                )
                notification_threads.append(thread)
            
            # Telegram bildirimi
            if settings.get("telegram_notification", False) and settings.get("telegram_chat_id"):
                thread = threading.Thread(
                    target=self._send_telegram_alert,
                    args=(settings["telegram_chat_id"], alert_message, event_data),
                    daemon=True
                )
                notification_threads.append(thread)
            
            # Desktop bildirimi
            if settings.get("desktop_notification", True):
                thread = threading.Thread(
                    target=self._send_desktop_alert,
                    args=(alert_message,),
                    daemon=True
                )
                notification_threads.append(thread)
            
            # Ses uyarısı
            if settings.get("sound_notification", True):
                thread = threading.Thread(
                    target=self._play_alert_sound,
                    daemon=True
                )
                notification_threads.append(thread)
            
            # Tüm thread'leri başlat
            for thread in notification_threads:
                thread.start()
            
            logging.info(f"Düşme uyarısı gönderildi - {len(notification_threads)} kanal")
            
        except Exception as e:
            logging.error(f"Düşme uyarısı gönderilirken hata: {str(e)}")
    
    def _check_cooldown(self, user_id: str) -> bool:
        """Bildirim cooldown kontrolü yapar"""
        current_time = time.time()
        last_time = self.last_notification_times.get(user_id, 0)
        
        if current_time - last_time < self.notification_cooldown:
            return False
        
        self.last_notification_times[user_id] = current_time
        return True
    
    def _prepare_alert_message(self, event_data: Dict) -> Dict:
        """Uyarı mesajını hazırlar"""
        timestamp = datetime.fromtimestamp(event_data.get("timestamp", time.time()))
        
        return {
            "title": "🚨 DÜŞME TESPİT EDİLDİ!",
            "short_message": f"Guard sistemi bir düşme tespit etti - {timestamp.strftime('%H:%M:%S')}",
            "detailed_message": f"""
DÜŞME UYARISI

📅 Tarih: {timestamp.strftime('%d/%m/%Y')}
🕐 Saat: {timestamp.strftime('%H:%M:%S')}
🎯 Güven Oranı: {event_data.get('confidence', 0):.1%}
📍 Konum: {event_data.get('location', 'Bilinmiyor')}
🆔 Olay ID: {event_data.get('id', 'N/A')}

Lütfen durumu kontrol edin!
            """.strip(),
            "timestamp": timestamp
        }
    
    def _send_email_alert(self, email: str, message: Dict, event_data: Dict):
        """E-posta uyarısı gönderir"""
        try:
            if not self.smtp_user or not self.smtp_pass:
                logging.warning("SMTP ayarları eksik, e-posta gönderilemedi")
                return
            
            # E-posta mesajını oluştur
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = email
            msg['Subject'] = message["title"]
            
            # HTML içerik
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #f44336; color: white; padding: 20px; text-align: center;">
                    <h1>🚨 DÜŞME UYARISI</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>Acil Durum Bildirimi</h2>
                    <p><strong>Guard sistemi bir düşme tespit etti!</strong></p>
                    
                    <table style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Tarih:</strong></td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{message["timestamp"].strftime('%d/%m/%Y')}</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Saat:</strong></td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{message["timestamp"].strftime('%H:%M:%S')}</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Güven Oranı:</strong></td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{event_data.get('confidence', 0):.1%}</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;"><strong>Konum:</strong></td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{event_data.get('location', 'Bilinmiyor')}</td>
                        </tr>
                    </table>
                    
                    <p style="margin-top: 20px; color: #f44336; font-weight: bold;">
                        Lütfen durumu hemen kontrol edin!
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Ekran görüntüsü varsa ekle
            screenshot_url = event_data.get("screenshot_url")
            if screenshot_url and screenshot_url.startswith("file://"):
                try:
                    image_path = screenshot_url.replace("file://", "")
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                        
                        img = MIMEImage(img_data)
                        img.add_header('Content-Disposition', 'attachment', filename='fall_detection.jpg')
                        msg.attach(img)
                except Exception as img_error:
                    logging.warning(f"Ekran görüntüsü e-postaya eklenemedi: {str(img_error)}")
            
            # E-postayı gönder
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, email, msg.as_string())
            
            logging.info(f"E-posta uyarısı gönderildi: {email}")
            
        except Exception as e:
            logging.error(f"E-posta gönderilirken hata: {str(e)}")
    
    def _send_sms_alert(self, phone_number: str, message: Dict):
        """SMS uyarısı gönderir"""
        try:
            if not self.twilio_client:
                logging.warning("Twilio client yok, SMS gönderilemedi")
                return
            
            sms_body = f"{message['title']}\n\n{message['short_message']}\n\nLütfen durumu kontrol edin!"
            
            message = self.twilio_client.messages.create(
                body=sms_body,
                from_=Settings.TWILIO_PHONE,
                to=phone_number
            )
            
            logging.info(f"SMS uyarısı gönderildi: {phone_number} - SID: {message.sid}")
            
        except Exception as e:
            logging.error(f"SMS gönderilirken hata: {str(e)}")
    
    def _send_telegram_alert(self, chat_id: str, message: Dict, event_data: Dict):
        """Telegram uyarısı gönderir"""
        try:
            if not self.telegram_token:
                logging.warning("Telegram token yok, mesaj gönderilemedi")
                return
            
            telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            telegram_message = f"""
🚨 *DÜŞME UYARISI*

📅 Tarih: {message["timestamp"].strftime('%d/%m/%Y')}
🕐 Saat: {message["timestamp"].strftime('%H:%M:%S')}
🎯 Güven: {event_data.get('confidence', 0):.1%}
📍 Konum: {event_data.get('location', 'Bilinmiyor')}

⚠️ *Lütfen durumu hemen kontrol edin!*
            """.strip()
            
            payload = {
                'chat_id': chat_id,
                'text': telegram_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(telegram_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logging.info(f"Telegram uyarısı gönderildi: {chat_id}")
                
                # Ekran görüntüsü varsa gönder
                screenshot_url = event_data.get("screenshot_url")
                if screenshot_url and screenshot_url.startswith("file://"):
                    self._send_telegram_photo(chat_id, screenshot_url)
            else:
                logging.error(f"Telegram mesajı gönderilemedi: {response.text}")
            
        except Exception as e:
            logging.error(f"Telegram mesajı gönderilirken hata: {str(e)}")
    
    def _send_telegram_photo(self, chat_id: str, photo_path: str):
        """Telegram'a fotoğraf gönderir"""
        try:
            photo_url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
            
            image_path = photo_path.replace("file://", "")
            if not os.path.exists(image_path):
                return
            
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': chat_id, 'caption': '📸 Düşme anı görüntüsü'}
                
                response = requests.post(photo_url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    logging.info("Telegram fotoğrafı gönderildi")
                else:
                    logging.error(f"Telegram fotoğrafı gönderilemedi: {response.text}")
                    
        except Exception as e:
            logging.error(f"Telegram fotoğrafı gönderilirken hata: {str(e)}")
    
    def _send_desktop_alert(self, message: Dict):
        """Desktop bildirimi gönderir"""
        try:
            if not DESKTOP_NOTIFICATION_AVAILABLE:
                logging.warning("Desktop bildirim desteği yok")
                return
            
            desktop_notification.notify(
                title=message["title"],
                message=message["short_message"],
                app_name="Guard",
                timeout=10
            )
            
            logging.info("Desktop bildirimi gönderildi")
            
        except Exception as e:
            logging.error(f"Desktop bildirimi gönderilirken hata: {str(e)}")
    
    def _play_alert_sound(self):
        """Uyarı sesi çalar"""
        try:
            if not SOUND_AVAILABLE:
                logging.warning("Ses desteği yok")
                return
            
            # Uyarı sesi dosyasını kontrol et
            sound_file = os.path.join("assets", "sounds", "alert.wav")
            
            if not os.path.exists(sound_file):
                # Basit beep sesi oluştur
                self._generate_beep_sound()
                return
            
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
            
            logging.info("Uyarı sesi çalındı")
            
        except Exception as e:
            logging.error(f"Ses çalınırken hata: {str(e)}")
    
    def _generate_beep_sound(self):
        """Basit beep sesi oluşturur"""
        try:
            # Platform bağımsız beep
            import sys
            if sys.platform == "win32":
                import winsound
                winsound.Beep(1000, 1000)  # 1000Hz, 1 saniye
            else:
                # Linux/Mac için basit beep
                os.system("echo -e '\a'")
                
        except Exception as e:
            logging.warning(f"Beep sesi oluşturulamadı: {str(e)}")
    
    def send_test_notification(self, user_id: str, notification_type: str = "all") -> bool:
        """Test bildirimi gönderir"""
        try:
            test_event = {
                "id": "test_" + str(int(time.time())),
                "timestamp": time.time(),
                "confidence": 0.95,
                "location": "Test Konumu",
                "screenshot_url": None
            }
            
            user_data = self.database_service.get_user_data(user_id)
            if not user_data:
                logging.error("Kullanıcı bulunamadı")
                return False
            
            # Geçici olarak cooldown'u atla
            original_cooldown = self.notification_cooldown
            self.notification_cooldown = 0
            
            self.send_fall_alert(user_id, test_event)
            
            # Cooldown'u geri yükle
            self.notification_cooldown = original_cooldown
            
            logging.info(f"Test bildirimi gönderildi: {notification_type}")
            return True
            
        except Exception as e:
            logging.error(f"Test bildirimi gönderilirken hata: {str(e)}")
            return False
    
    def update_notification_settings(self, user_id: str, settings: Dict) -> bool:
        """Bildirim ayarlarını günceller"""
        try:
            return self.database_service.save_user_settings(user_id, settings)
        except Exception as e:
            logging.error(f"Bildirim ayarları güncellenirken hata: {str(e)}")
            return False

# Global notification service instance'ı
_notification_service_instance = None

def get_notification_service() -> NotificationService:
    """Global NotificationService instance'ını döndürür"""
    global _notification_service_instance
    if _notification_service_instance is None:
        _notification_service_instance = NotificationService()
    return _notification_service_instance