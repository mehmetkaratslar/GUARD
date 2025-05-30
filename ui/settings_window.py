# =======================================================================================
# 📄 Dosya Adı   : settings_window.py
# 📁 Konum       : guard_pc/ui/settings_window.py
# 📌 Açıklama    : Kullanıcı ayarları penceresi
#                 - Bildirim tercihleri
#                 - Kamera ve model ayarları
#                 - Kullanıcı profil bilgileri
#
# 🔗 Bağlantılı Dosyalar:
#   - services/database_service.py     : Ayarları kaydetme
#   - services/notification_service.py : Bildirim ayarları
#   - config/settings.py              : Sistem ayarları
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Callable, Optional

from services.database_service import get_database_service
from services.notification_service import get_notification_service
from config.settings import Settings

class SettingsWindow:
    """Ayarlar penceresi sınıfı"""
    
    def __init__(self, parent, user_data: Dict, callback: Callable = None):
        """Ayarlar penceresini başlatır"""
        self.parent = parent
        self.user_data = user_data
        self.user_id = user_data['uid']
        self.callback = callback
        
        # Servisler
        self.database_service = get_database_service()
        self.notification_service = get_notification_service()
        
        # Pencere
        self.window = None
        
        # Ayar değişkenleri
        self.settings_vars = {}
        
        # Mevcut ayarları yükle
        self.current_settings = self._load_current_settings()
        
        # Pencereyi oluştur ve göster
        self.create_window()
        
        logging.info(f"SettingsWindow açıldı - Kullanıcı: {user_data['email']}")
    
    def _load_current_settings(self) -> Dict:
        """Mevcut ayarları yükler"""
        try:
            user_data = self.database_service.get_user_data(self.user_id)
            if user_data and 'settings' in user_data:
                return user_data['settings']
            else:
                return Settings.DEFAULT_NOTIFICATION_SETTINGS.copy()
                
        except Exception as e:
            logging.error(f"Ayarlar yüklenirken hata: {str(e)}")
            return Settings.DEFAULT_NOTIFICATION_SETTINGS.copy()
    
    def create_window(self):
        """Ayarlar penceresini oluşturur"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Guard - Ayarlar")
        self.window.geometry("500x700")
        self.window.resizable(False, False)
        
        # Modal pencere yap
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Pencereyi ortala
        self._center_window()
        
        # UI bileşenlerini oluştur
        self._create_widgets()
        
        # Pencere kapatma olayı
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _center_window(self):
        """Pencereyi üst pencereye göre ortalar"""
        self.window.update_idletasks()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        window_width = self.window.winfo_reqwidth()
        window_height = self.window.winfo_reqheight()
        
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _create_widgets(self):
        """UI bileşenlerini oluşturur"""
        # Ana frame
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_label = ttk.Label(
            main_frame,
            text="Ayarlar",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Notebook widget (tab'lar için)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Tab'ları oluştur
        self._create_notification_tab(notebook)
        self._create_camera_tab(notebook)
        self._create_profile_tab(notebook)
        self._create_advanced_tab(notebook)
        
        # Alt butonlar
        self._create_buttons(main_frame)
    
    def _create_notification_tab(self, notebook):
        """Bildirim ayarları tab'ı"""
        tab_frame = ttk.Frame(notebook, padding="20")
        notebook.add(tab_frame, text="Bildirimler")
        
        # E-posta bildirimleri
        email_frame = ttk.LabelFrame(tab_frame, text="E-posta Bildirimleri", padding="10")
        email_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.settings_vars['email_notification'] = tk.BooleanVar(
            value=self.current_settings.get('email_notification', True)
        )
        ttk.Checkbutton(
            email_frame,
            text="E-posta bildirimleri gönder",
            variable=self.settings_vars['email_notification']
        ).pack(anchor=tk.W)
        
        # SMS bildirimleri
        sms_frame = ttk.LabelFrame(tab_frame, text="SMS Bildirimleri", padding="10")
        sms_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.settings_vars['sms_notification'] = tk.BooleanVar(
            value=self.current_settings.get('sms_notification', False)
        )
        sms_check = ttk.Checkbutton(
            sms_frame,
            text="SMS bildirimleri gönder",
            variable=self.settings_vars['sms_notification']
        )
        sms_check.pack(anchor=tk.W)
        
        # Telefon numarası
        ttk.Label(sms_frame, text="Telefon Numarası:").pack(anchor=tk.W, pady=(10, 0))
        self.settings_vars['phone_number'] = tk.StringVar(
            value=self.current_settings.get('phone_number', '')
        )
        phone_entry = ttk.Entry(
            sms_frame,
            textvariable=self.settings_vars['phone_number'],
            width=20
        )
        phone_entry.pack(anchor=tk.W, pady=(5, 0))
        
        # Telegram bildirimleri
        telegram_frame = ttk.LabelFrame(tab_frame, text="Telegram Bildirimleri", padding="10")
        telegram_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.settings_vars['telegram_notification'] = tk.BooleanVar(
            value=self.current_settings.get('telegram_notification', False)
        )
        telegram_check = ttk.Checkbutton(
            telegram_frame,
            text="Telegram bildirimleri gönder",
            variable=self.settings_vars['telegram_notification']
        )
        telegram_check.pack(anchor=tk.W)
        
        # Telegram Chat ID
        ttk.Label(telegram_frame, text="Telegram Chat ID:").pack(anchor=tk.W, pady=(10, 0))
        self.settings_vars['telegram_chat_id'] = tk.StringVar(
            value=self.current_settings.get('telegram_chat_id', '')
        )
        telegram_entry = ttk.Entry(
            telegram_frame,
            textvariable=self.settings_vars['telegram_chat_id'],
            width=20
        )
        telegram_entry.pack(anchor=tk.W, pady=(5, 0))
        
        # Desktop bildirimleri
        desktop_frame = ttk.LabelFrame(tab_frame, text="Desktop Bildirimleri", padding="10")
        desktop_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.settings_vars['desktop_notification'] = tk.BooleanVar(
            value=self.current_settings.get('desktop_notification', True)
        )
        ttk.Checkbutton(
            desktop_frame,
            text="Masaüstü bildirimleri göster",
            variable=self.settings_vars['desktop_notification']
        ).pack(anchor=tk.W)
        
        # Ses bildirimleri
        self.settings_vars['sound_notification'] = tk.BooleanVar(
            value=self.current_settings.get('sound_notification', True)
        )
        ttk.Checkbutton(
            desktop_frame,
            text="Ses uyarıları çal",
            variable=self.settings_vars['sound_notification']
        ).pack(anchor=tk.W)
    
    def _create_camera_tab(self, notebook):
        """Kamera ayarları tab'ı"""
        tab_frame = ttk.Frame(notebook, padding="20")
        notebook.add(tab_frame, text="Kamera")
        
        # Kamera seçimi
        camera_frame = ttk.LabelFrame(tab_frame, text="Kamera Ayarları", padding="10")
        camera_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(camera_frame, text="Kamera İndeksi:").pack(anchor=tk.W)
        self.settings_vars['camera_index'] = tk.StringVar(
            value=str(self.current_settings.get('camera_index', Settings.CAMERA_INDEX))
        )
        camera_entry = ttk.Entry(
            camera_frame,
            textvariable=self.settings_vars['camera_index'],
            width=10
        )
        camera_entry.pack(anchor=tk.W, pady=(5, 10))
        
        # Çözünürlük ayarları
        resolution_frame = ttk.Frame(camera_frame)
        resolution_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(resolution_frame, text="Çözünürlük:").pack(anchor=tk.W)
        
        res_controls = ttk.Frame(resolution_frame)
        res_controls.pack(anchor=tk.W, pady=(5, 0))
        
        ttk.Label(res_controls, text="Genişlik:").pack(side=tk.LEFT)
        self.settings_vars['camera_width'] = tk.StringVar(
            value=str(self.current_settings.get('camera_width', Settings.CAMERA_WIDTH))
        )
        width_entry = ttk.Entry(res_controls, textvariable=self.settings_vars['camera_width'], width=8)
        width_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(res_controls, text="Yükseklik:").pack(side=tk.LEFT)
        self.settings_vars['camera_height'] = tk.StringVar(
            value=str(self.current_settings.get('camera_height', Settings.CAMERA_HEIGHT))
        )
        height_entry = ttk.Entry(res_controls, textvariable=self.settings_vars['camera_height'], width=8)
        height_entry.pack(side=tk.LEFT, padx=5)
        
        # Model ayarları
        model_frame = ttk.LabelFrame(tab_frame, text="Düşme Tespit Ayarları", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="Güven Eşiği (%):").pack(anchor=tk.W)
        self.settings_vars['confidence_threshold'] = tk.DoubleVar(
            value=self.current_settings.get('confidence_threshold', Settings.CONFIDENCE_THRESHOLD) * 100
        )
        
        threshold_frame = ttk.Frame(model_frame)
        threshold_frame.pack(anchor=tk.W, pady=(5, 0))
        
        threshold_scale = ttk.Scale(
            threshold_frame,
            from_=50,
            to=95,
            variable=self.settings_vars['confidence_threshold'],
            orient=tk.HORIZONTAL,
            length=200
        )
        threshold_scale.pack(side=tk.LEFT)
        
        threshold_label = ttk.Label(threshold_frame, text="70%")
        threshold_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Scale değer güncellemesi
        def update_threshold_label(value):
            threshold_label.config(text=f"{float(value):.0f}%")
        
        threshold_scale.configure(command=update_threshold_label)
        update_threshold_label(self.settings_vars['confidence_threshold'].get())
    
    def _create_profile_tab(self, notebook):
        """Profil bilgileri tab'ı"""
        tab_frame = ttk.Frame(notebook, padding="20")
        notebook.add(tab_frame, text="Profil")
        
        # Kullanıcı bilgileri
        profile_frame = ttk.LabelFrame(tab_frame, text="Kullanıcı Bilgileri", padding="10")
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Resim (varsa)
        if self.user_data.get('picture'):
            try:
                # Profil resmi yüklenebilir (isteğe bağlı)
                pass
            except Exception:
                pass
        
        # Ad
        ttk.Label(profile_frame, text="Ad:").pack(anchor=tk.W)
        name_label = ttk.Label(
            profile_frame,
            text=self.user_data.get('name', 'Bilinmiyor'),
            font=('Arial', 10, 'bold')
        )
        name_label.pack(anchor=tk.W, pady=(0, 10))
        
        # E-posta
        ttk.Label(profile_frame, text="E-posta:").pack(anchor=tk.W)
        email_label = ttk.Label(
            profile_frame,
            text=self.user_data.get('email', 'Bilinmiyor'),
            font=('Arial', 10)
        )
        email_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Kullanıcı ID
        ttk.Label(profile_frame, text="Kullanıcı ID:").pack(anchor=tk.W)
        uid_label = ttk.Label(
            profile_frame,
            text=self.user_data.get('uid', 'Bilinmiyor'),
            font=('Arial', 9),
            foreground='gray'
        )
        uid_label.pack(anchor=tk.W, pady=(0, 10))
        
        # İstatistikler
        stats_frame = ttk.LabelFrame(tab_frame, text="İstatistikler", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        try:
            stats = self.database_service.get_user_stats(self.user_id)
            
            stats_text = f"""
Toplam Düşme Olayı: {stats.get('total_events', 0)}
Bugünkü Olaylar: {stats.get('events_today', 0)}
Bu Haftaki Olaylar: {stats.get('events_this_week', 0)}
Bu Ayki Olaylar: {stats.get('events_this_month', 0)}
            """.strip()
            
            stats_label = ttk.Label(stats_frame, text=stats_text, font=('Arial', 9))
            stats_label.pack(anchor=tk.W)
            
        except Exception as e:
            ttk.Label(stats_frame, text="İstatistikler yüklenemedi").pack(anchor=tk.W)
    
    def _create_advanced_tab(self, notebook):
        """Gelişmiş ayarlar tab'ı"""
        tab_frame = ttk.Frame(notebook, padding="20")
        notebook.add(tab_frame, text="Gelişmiş")
        
        # Sistem ayarları
        system_frame = ttk.LabelFrame(tab_frame, text="Sistem Ayarları", padding="10")
        system_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Otomatik başlatma
        self.settings_vars['auto_start_detection'] = tk.BooleanVar(
            value=self.current_settings.get('auto_start_detection', False)
        )
        ttk.Checkbutton(
            system_frame,
            text="Uygulama açılışında tespiti otomatik başlat",
            variable=self.settings_vars['auto_start_detection']
        ).pack(anchor=tk.W, pady=2)
        
        # Otomatik streaming
        self.settings_vars['auto_start_streaming'] = tk.BooleanVar(
            value=self.current_settings.get('auto_start_streaming', False)
        )
        ttk.Checkbutton(
            system_frame,
            text="Uygulama açılışında streaming'i otomatik başlat",
            variable=self.settings_vars['auto_start_streaming']
        ).pack(anchor=tk.W, pady=2)
        
        # Debug modu
        self.settings_vars['debug_mode'] = tk.BooleanVar(
            value=self.current_settings.get('debug_mode', False)
        )
        ttk.Checkbutton(
            system_frame,
            text="Debug modu (geliştiriciler için)",
            variable=self.settings_vars['debug_mode']
        ).pack(anchor=tk.W, pady=2)
        
        # Depolama ayarları
        storage_frame = ttk.LabelFrame(tab_frame, text="Depolama Ayarları", padding="10")
        storage_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Eski olayları temizle
        ttk.Label(storage_frame, text="Eski olayları otomatik sil (gün):").pack(anchor=tk.W)
        self.settings_vars['auto_delete_days'] = tk.StringVar(
            value=str(self.current_settings.get('auto_delete_days', 30))
        )
        days_entry = ttk.Entry(
            storage_frame,
            textvariable=self.settings_vars['auto_delete_days'],
            width=10
        )
        days_entry.pack(anchor=tk.W, pady=(5, 10))
        
        # Temizlik butonu
        cleanup_button = ttk.Button(
            storage_frame,
            text="Eski Verileri Şimdi Temizle",
            command=self._cleanup_old_data
        )
        cleanup_button.pack(anchor=tk.W)
        
        # Test butonu
        test_frame = ttk.LabelFrame(tab_frame, text="Test İşlemleri", padding="10")
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        test_notification_button = ttk.Button(
            test_frame,
            text="Test Bildirimi Gönder",
            command=self._test_notifications
        )
        test_notification_button.pack(fill=tk.X, pady=2)
    
    def _create_buttons(self, parent):
        """Alt butonları oluşturur"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        # İptal butonu
        cancel_button = ttk.Button(
            button_frame,
            text="İptal",
            command=self._on_cancel
        )
        cancel_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Kaydet butonu
        save_button = ttk.Button(
            button_frame,
            text="Kaydet",
            command=self._save_settings
        )
        save_button.pack(side=tk.RIGHT)
        
        # Varsayılana sıfırla butonu
        reset_button = ttk.Button(
            button_frame,
            text="Varsayılana Sıfırla",
            command=self._reset_to_defaults
        )
        reset_button.pack(side=tk.LEFT)
    
    def _save_settings(self):
        """Ayarları kaydeder"""
        try:
            # Form verilerini topla
            new_settings = {}
            
            # Bildirim ayarları
            new_settings['email_notification'] = self.settings_vars['email_notification'].get()
            new_settings['sms_notification'] = self.settings_vars['sms_notification'].get()
            new_settings['telegram_notification'] = self.settings_vars['telegram_notification'].get()
            new_settings['desktop_notification'] = self.settings_vars['desktop_notification'].get()
            new_settings['sound_notification'] = self.settings_vars['sound_notification'].get()
            
            new_settings['phone_number'] = self.settings_vars['phone_number'].get().strip()
            new_settings['telegram_chat_id'] = self.settings_vars['telegram_chat_id'].get().strip()
            
            # Kamera ayarları
            try:
                new_settings['camera_index'] = int(self.settings_vars['camera_index'].get())
                new_settings['camera_width'] = int(self.settings_vars['camera_width'].get())
                new_settings['camera_height'] = int(self.settings_vars['camera_height'].get())
                new_settings['confidence_threshold'] = self.settings_vars['confidence_threshold'].get() / 100.0
            except ValueError as e:
                messagebox.showerror("Hata", f"Geçersiz sayısal değer: {str(e)}")
                return
            
            # Gelişmiş ayarlar
            new_settings['auto_start_detection'] = self.settings_vars['auto_start_detection'].get()
            new_settings['auto_start_streaming'] = self.settings_vars['auto_start_streaming'].get()
            new_settings['debug_mode'] = self.settings_vars['debug_mode'].get()
            
            try:
                new_settings['auto_delete_days'] = int(self.settings_vars['auto_delete_days'].get())
            except ValueError:
                new_settings['auto_delete_days'] = 30
            
            # Ayarları kaydet
            success = self.database_service.save_user_settings(self.user_id, new_settings)
            
            if success:
                messagebox.showinfo("Başarılı", "Ayarlar kaydedildi!")
                
                # Callback'i çağır
                if self.callback:
                    self.callback()
                
                # Pencereyi kapat
                self.window.destroy()
            else:
                messagebox.showerror("Hata", "Ayarlar kaydedilemedi!")
                
        except Exception as e:
            logging.error(f"Ayarlar kaydedilirken hata: {str(e)}")
            messagebox.showerror("Hata", f"Ayarlar kaydedilirken hata:\n{str(e)}")
    
    def _reset_to_defaults(self):
        """Ayarları varsayılana sıfırlar"""
        response = messagebox.askyesno(
            "Varsayılana Sıfırla",
            "Tüm ayarları varsayılan değerlere sıfırlamak istediğinize emin misiniz?"
        )
        
        if response:
            try:
                # Varsayılan değerleri ayarla
                defaults = Settings.DEFAULT_NOTIFICATION_SETTINGS.copy()
                defaults.update({
                    'camera_index': Settings.CAMERA_INDEX,
                    'camera_width': Settings.CAMERA_WIDTH,
                    'camera_height': Settings.CAMERA_HEIGHT,
                    'confidence_threshold': Settings.CONFIDENCE_THRESHOLD,
                    'auto_start_detection': False,
                    'auto_start_streaming': False,
                    'debug_mode': False,
                    'auto_delete_days': 30,
                    'phone_number': '',
                    'telegram_chat_id': ''
                })
                
                # UI'yi güncelle
                for key, value in defaults.items():
                    if key in self.settings_vars:
                        if isinstance(value, bool):
                            self.settings_vars[key].set(value)
                        elif key == 'confidence_threshold':
                            self.settings_vars[key].set(value * 100)
                        else:
                            self.settings_vars[key].set(str(value))
                
                messagebox.showinfo("Başarılı", "Ayarlar varsayılan değerlere sıfırlandı!")
                
            except Exception as e:
                logging.error(f"Varsayılana sıfırlama hatası: {str(e)}")
                messagebox.showerror("Hata", f"Sıfırlama sırasında hata:\n{str(e)}")
    
    def _test_notifications(self):
        """Test bildirimi gönderir"""
        try:
            success = self.notification_service.send_test_notification(self.user_id)
            
            if success:
                messagebox.showinfo("Test Bildirimi", "Test bildirimi gönderildi!")
            else:
                messagebox.showerror("Hata", "Test bildirimi gönderilemedi!")
                
        except Exception as e:
            logging.error(f"Test bildirimi hatası: {str(e)}")
            messagebox.showerror("Hata", f"Test bildirimi sırasında hata:\n{str(e)}")
    
    def _cleanup_old_data(self):
        """Eski verileri temizler"""
        response = messagebox.askyesno(
            "Veri Temizliği",
            "Eski veriler silinecek. Bu işlem geri alınamaz.\n\nDevam etmek istiyor musunuz?"
        )
        
        if response:
            try:
                # Eski olayları temizle
                deleted_events = self.database_service.cleanup_old_events(self.user_id)
                
                # Eski ekran görüntülerini temizle
                from services.storage_service import get_storage_service
                storage_service = get_storage_service()
                deleted_screenshots = storage_service.cleanup_old_screenshots(self.user_id)
                
                messagebox.showinfo(
                    "Temizlik Tamamlandı",
                    f"Temizlik tamamlandı!\n\n"
                    f"Silinen olay sayısı: {deleted_events}\n"
                    f"Silinen görüntü sayısı: {deleted_screenshots}"
                )
                
            except Exception as e:
                logging.error(f"Veri temizliği hatası: {str(e)}")
                messagebox.showerror("Hata", f"Veri temizliği sırasında hata:\n{str(e)}")
    
    def _on_cancel(self):
        """İptal butonuna basıldığında"""
        self.window.destroy()
    
    def _on_window_close(self):
        """Pencere kapatma olayını işler"""
        self.window.destroy()

# Test fonksiyonu
def test_settings_window():
    """Settings window'u test eder"""
    try:
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()  # Ana pencereyi gizle
        
        test_user = {
            'uid': 'test_user',
            'email': 'test@example.com',
            'name': 'Test Kullanıcı'
        }
        
        settings_window = SettingsWindow(root, test_user)
        root.mainloop()
        
    except Exception as e:
        logging.error(f"Test sırasında hata: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_settings_window()