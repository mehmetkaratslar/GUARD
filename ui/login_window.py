# =======================================================================================
# 📄 Dosya Adı   : login_window.py
# 📁 Konum       : guard_pc/ui/login_window.py
# 📌 Açıklama    : Kullanıcı giriş ve kayıt penceresi
#                 - Google OAuth entegrasyonu
#                 - Kullanıcı kimlik doğrulama
#                 - Ana pencereye geçiş
#
# 🔗 Bağlantılı Dosyalar:
#   - services/auth_service.py  : Authentication işlemleri
#   - ui/main_window.py        : Ana uygulama penceresi
#   - ui/styles.py             : UI stil tanımları
#   - config/settings.py       : GUI ayarları
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from PIL import Image, ImageTk
import os
from typing import Optional

from config.settings import Settings
from services.auth_service import get_auth_service
from services.database_service import get_database_service

class LoginWindow:
    """Giriş/Kayıt penceresi sınıfı"""
    
    def __init__(self):
        """Login penceresini başlatır"""
        self.root = None
        self.auth_service = get_auth_service()
        self.database_service = get_database_service()
        
        # UI bileşenleri
        self.status_label = None
        self.login_button = None
        self.progress_bar = None
        
        # Durum
        self.is_authenticating = False
        
        logging.info("LoginWindow oluşturuldu")
    
    def create_window(self):
        """Ana pencereyi oluşturur"""
        self.root = tk.Tk()
        self.root.title(f"{Settings.APP_NAME} - Giriş")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        # İkon ayarla (varsa)
        try:
            icon_path = os.path.join("assets", "icons", "guard_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            logging.warning(f"İkon yüklenemedi: {str(e)}")
        
        # Pencereyi ortala
        self._center_window()
        
        # Stil ayarları
        self._setup_styles()
        
        # UI bileşenlerini oluştur
        self._create_widgets()
        
        # Pencere kapatma olayı
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _center_window(self):
        """Pencereyi ekranın ortasında konumlandırır"""
        self.root.update_idletasks()
        
        window_width = self.root.winfo_reqwidth()
        window_height = self.root.winfo_reqheight()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _setup_styles(self):
        """Stil ayarlarını yapar"""
        style = ttk.Style()
        
        # Tema seçimi
        try:
            if Settings.THEME_MODE == "dark":
                style.theme_use('clam')
            else:
                style.theme_use('default')
        except Exception as e:
            logging.warning(f"Tema ayarlanamadı: {str(e)}")
            style.theme_use('default')
        
        # Özel stiller
        style.configure('Title.TLabel', font=('Arial', 24, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12))
        style.configure('Large.TButton', font=('Arial', 12, 'bold'), padding=10)
        style.configure('Status.TLabel', font=('Arial', 10))
    
    def _create_widgets(self):
        """UI bileşenlerini oluşturur"""
        # Ana frame
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/başlık alanı
        self._create_header(main_frame)
        
        # Spacer
        ttk.Frame(main_frame, height=30).pack()
        
        # Giriş alanı
        self._create_login_section(main_frame)
        
        # Spacer
        ttk.Frame(main_frame, height=30).pack()
        
        # Durum alanı
        self._create_status_section(main_frame)
        
        # Footer
        self._create_footer(main_frame)
    
    def _create_header(self, parent):
        """Başlık alanını oluşturur"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Logo (varsa)
        try:
            logo_path = os.path.join("assets", "images", "guard_logo.png")
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path)
                logo_image = logo_image.resize((80, 80), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_image)
                
                logo_label = ttk.Label(header_frame, image=logo_photo)
                logo_label.image = logo_photo  # Referansı sakla
                logo_label.pack(pady=(0, 10))
        except Exception as e:
            logging.debug(f"Logo yüklenemedi: {str(e)}")
        
        # Başlık
        title_label = ttk.Label(
            header_frame,
            text=Settings.APP_NAME,
            style='Title.TLabel'
        )
        title_label.pack()
        
        # Alt başlık
        subtitle_label = ttk.Label(
            header_frame,
            text="Gerçek Zamanlı Düşme Algılama Sistemi",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Versiyon
        version_label = ttk.Label(
            header_frame,
            text=f"v{Settings.APP_VERSION}",
            font=('Arial', 8)
        )
        version_label.pack(pady=(5, 0))
    
    def _create_login_section(self, parent):
        """Giriş bölümünü oluşturur"""
        login_frame = ttk.LabelFrame(parent, text="Giriş Yap", padding="20")
        login_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Açıklama
        info_label = ttk.Label(
            login_frame,
            text="Guard'ı kullanmak için Google hesabınızla giriş yapın.",
            style='Subtitle.TLabel'
        )
        info_label.pack(pady=(0, 20))
        
        # Google giriş butonu
        self.login_button = ttk.Button(
            login_frame,
            text="🔐 Google ile Giriş Yap",
            style='Large.TButton',
            command=self._start_google_login
        )
        self.login_button.pack(pady=10)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            login_frame,
            mode='indeterminate',
            length=300
        )
        self.progress_bar.pack(pady=(10, 0))
        self.progress_bar.pack_forget()  # Başlangıçta gizle
        
        # Offline mod butonu
        offline_button = ttk.Button(
            login_frame,
            text="🔄 Çevrimdışı Modda Devam Et",
            command=self._start_offline_mode
        )
        offline_button.pack(pady=(10, 0))
    
    def _create_status_section(self, parent):
        """Durum bölümünü oluşturur"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Durum etiketi
        self.status_label = ttk.Label(
            status_frame,
            text="Giriş yapmak için yukarıdaki butona tıklayın",
            style='Status.TLabel',
            foreground='gray'
        )
        self.status_label.pack()
        
        # Sistem durumu bilgileri
        self._create_system_status(status_frame)
    
    def _create_system_status(self, parent):
        """Sistem durumu bilgilerini oluşturur"""
        status_frame = ttk.LabelFrame(parent, text="Sistem Durumu", padding="10")
        status_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Firebase durumu
        firebase_status = "✅ Bağlı" if self._check_firebase_connection() else "❌ Bağlanamadı"
        firebase_label = ttk.Label(status_frame, text=f"Firebase: {firebase_status}")
        firebase_label.pack(anchor=tk.W)
        
        # Model durumu
        model_status = "✅ Yüklendi" if self._check_model_status() else "❌ Yüklenemedi"
        model_label = ttk.Label(status_frame, text=f"AI Model: {model_status}")
        model_label.pack(anchor=tk.W)
        
        # Kamera durumu
        camera_status = "✅ Hazır" if self._check_camera_status() else "❌ Bulunamadı"
        camera_label = ttk.Label(status_frame, text=f"Kamera: {camera_status}")
        camera_label.pack(anchor=tk.W)
    
    def _create_footer(self, parent):
        """Footer alanını oluşturur"""
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bilgi metni
        info_text = (
            "Bu uygulama yaşlılar ve hassas bireyler için gerçek zamanlı düşme "
            "algılama sistemidir. Gizlilik ve güvenlik en üst düzeyde korunmaktadır."
        )
        
        info_label = ttk.Label(
            footer_frame,
            text=info_text,
            font=('Arial', 8),
            foreground='gray',
            wraplength=400,
            justify=tk.CENTER
        )
        info_label.pack(pady=10)
    
    def _check_firebase_connection(self) -> bool:
        """Firebase bağlantısını kontrol eder"""
        try:
            from config.firebase_config import is_firebase_connected
            return is_firebase_connected()
        except Exception:
            return False
    
    def _check_model_status(self) -> bool:
        """Model durumunu kontrol eder"""
        try:
            from models.fall_detector import get_fall_detector
            detector = get_fall_detector()
            return detector.is_loaded
        except Exception:
            return False
    
    def _check_camera_status(self) -> bool:
        """Kamera durumunu kontrol eder"""
        try:
            import cv2
            cap = cv2.VideoCapture(Settings.CAMERA_INDEX)
            is_opened = cap.isOpened()
            cap.release()
            return is_opened
        except Exception:
            return False
    
    def _start_google_login(self):
        """Google OAuth giriş sürecini başlatır"""
        if self.is_authenticating:
            return
        
        try:
            self.is_authenticating = True
            self._update_ui_state(True)
            
            # Auth service callback'lerini ayarla
            self.auth_service.start_oauth_flow(
                success_callback=self._on_login_success,
                error_callback=self._on_login_error
            )
            
        except Exception as e:
            logging.error(f"Google giriş başlatılırken hata: {str(e)}")
            self._on_login_error(str(e))
    
    def _start_offline_mode(self):
        """Çevrimdışı modda devam eder"""
        try:
            # Dummy kullanıcı oluştur
            offline_user = {
                'uid': 'offline_user',
                'email': 'offline@guard.local',
                'name': 'Çevrimdışı Kullanıcı',
                'picture': '',
                'verified_email': False
            }
            
            # Veritabanına kaydet
            self.database_service.create_new_user('offline_user', offline_user)
            
            self._update_status("Çevrimdışı modda giriş yapıldı", "green")
            
            # Ana pencereyi aç
            self._open_main_window(offline_user)
            
        except Exception as e:
            logging.error(f"Çevrimdışı mod başlatılırken hata: {str(e)}")
            self._update_status(f"Hata: {str(e)}", "red")
    
    def _on_login_success(self, user_data):
        """Başarılı giriş callback'i"""
        try:
            logging.info(f"Giriş başarılı: {user_data['email']}")
            
            # UI'yi ana thread'de güncelle
            self.root.after(0, lambda: self._handle_login_success(user_data))
            
        except Exception as e:
            logging.error(f"Login success handler hatası: {str(e)}")
            self._on_login_error(str(e))
    
    def _handle_login_success(self, user_data):
        """Ana thread'de giriş başarısını işler"""
        try:
            # Kullanıcıyı veritabanına kaydet/güncelle
            self.database_service.create_new_user(user_data['uid'], user_data)
            self.database_service.update_last_login(user_data['uid'])
            
            self._update_status("Giriş başarılı! Ana pencere açılıyor...", "green")
            
            # Kısa gecikme sonrası ana pencereyi aç
            self.root.after(1000, lambda: self._open_main_window(user_data))
            
        except Exception as e:
            logging.error(f"Login success işlenirken hata: {str(e)}")
            self._update_status(f"Hata: {str(e)}", "red")
            self._update_ui_state(False)
    
    def _on_login_error(self, error_message):
        """Giriş hatası callback'i"""
        logging.error(f"Giriş hatası: {error_message}")
        
        # UI'yi ana thread'de güncelle
        self.root.after(0, lambda: self._handle_login_error(error_message))
    
    def _handle_login_error(self, error_message):
        """Ana thread'de giriş hatasını işler"""
        self._update_status(f"Giriş hatası: {error_message}", "red")
        self._update_ui_state(False)
        
        # Hata mesajı göster
        messagebox.showerror(
            "Giriş Hatası",
            f"Google ile giriş yapılırken hata oluştu:\n\n{error_message}\n\n"
            "Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin."
        )
    
    def _update_ui_state(self, is_loading: bool):
        """UI durumunu günceller"""
        if is_loading:
            self.login_button.config(state='disabled', text="Giriş yapılıyor...")
            self.progress_bar.pack(pady=(10, 0))
            self.progress_bar.start()
            self._update_status("Google OAuth sayfası açılıyor...", "blue")
        else:
            self.login_button.config(state='normal', text="🔐 Google ile Giriş Yap")
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.is_authenticating = False
    
    def _update_status(self, message: str, color: str = "black"):
        """Durum mesajını günceller"""
        if self.status_label:
            self.status_label.config(text=message, foreground=color)
            logging.info(f"Status: {message}")
    
    def _open_main_window(self, user_data):
        """Ana pencereyi açar"""
        try:
            # Login penceresini gizle
            self.root.withdraw()
            
            # Ana pencereyi import et ve aç
            from ui.main_window import MainWindow
            
            main_window = MainWindow(user_data)
            main_window.run()
            
            # Ana pencere kapandıktan sonra login penceresini kapat
            self.root.quit()
            
        except Exception as e:
            logging.error(f"Ana pencere açılırken hata: {str(e)}")
            messagebox.showerror(
                "Uygulama Hatası",
                f"Ana pencere açılırken hata oluştu:\n\n{str(e)}"
            )
            
            # Login penceresini tekrar göster
            self.root.deiconify()
            self._update_ui_state(False)
    
    def _on_window_close(self):
        """Pencere kapatma olayını işler"""
        try:
            if self.is_authenticating:
                response = messagebox.askyesno(
                    "Çıkış",
                    "Giriş işlemi devam ediyor. Yine de çıkmak istiyor musunuz?"
                )
                if not response:
                    return
            
            logging.info("Login penceresi kapatılıyor")
            self.root.quit()
            
        except Exception as e:
            logging.error(f"Pencere kapatılırken hata: {str(e)}")
            self.root.quit()
    
    def run(self):
        """Pencereyi çalıştırır"""
        try:
            self.create_window()
            
            logging.info("Login penceresi başlatılıyor")
            self.root.mainloop()
            
        except Exception as e:
            logging.error(f"Login penceresi çalışırken hata: {str(e)}")
            raise e
        finally:
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass

# Test fonksiyonu
def test_login_window():
    """Login window'u test eder"""
    try:
        # Logging'i başlat
        logging.basicConfig(level=logging.INFO)
        
        # Login window'u oluştur ve çalıştır
        login_window = LoginWindow()
        login_window.run()
        
    except Exception as e:
        logging.error(f"Test sırasında hata: {str(e)}")

if __name__ == "__main__":
    test_login_window()