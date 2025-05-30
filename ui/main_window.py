# =======================================================================================
# 📄 Dosya Adı   : main_window.py
# 📁 Konum       : guard_pc/ui/main_window.py
# 📌 Açıklama    : Ana uygulama penceresi
#                 - Kamera görüntüsü ve canlı izleme
#                 - Düşme tespiti kontrolü
#                 - Sistem durumu ve istatistikler
#                 - Ayarlar ve bildirim yönetimi
#
# 🔗 Bağlantılı Dosyalar:
#   - services/camera_service.py    : Kamera ve tespit işlemleri
#   - services/streaming_service.py : Canlı yayın
#   - services/notification_service.py : Bildirimmler
#   - ui/settings_window.py        : Ayarlar penceresi
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import logging
from typing import Dict, Optional
import webbrowser

from config.settings import Settings
from services.camera_service import get_camera_service, initialize_camera_service
from services.streaming_service import get_streaming_service, initialize_streaming
from services.database_service import get_database_service
from services.notification_service import get_notification_service

class MainWindow:
    """Ana uygulama penceresi sınıfı"""
    
    def __init__(self, user_data: Dict):
        """Ana pencereyi başlatır"""
        self.user_data = user_data
        self.user_id = user_data['uid']
        
        # Pencere ve UI
        self.root = None
        self.video_label = None
        self.status_label = None
        self.detection_status_label = None
        
        # Servisler
        self.camera_service = initialize_camera_service(self.user_id)
        self.streaming_service = get_streaming_service()
        self.database_service = get_database_service()
        self.notification_service = get_notification_service()
        
        # UI kontrol değişkenleri
        self.is_camera_running = tk.BooleanVar(value=False)
        self.is_detection_active = tk.BooleanVar(value=False)
        self.is_streaming_active = tk.BooleanVar(value=False)
        
        # UI bileşenleri
        self.start_button = None
        self.detection_button = None
        self.streaming_button = None
        self.stats_frame = None
        
        # Video güncelleme
        self.video_update_job = None
        self.stats_update_job = None
        
        # İstatistikler
        self.total_detections = 0
        self.last_detection_time = None
        self.session_start_time = time.time()
        
        logging.info(f"MainWindow oluşturuldu - Kullanıcı: {user_data['email']}")
    
    def create_window(self):
        """Ana pencereyi oluşturur"""
        self.root = tk.Tk()
        self.root.title(f"{Settings.APP_NAME} - {self.user_data['name']}")
        self.root.geometry(f"{Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT}")
        self.root.minsize(Settings.MIN_WINDOW_WIDTH, Settings.MIN_WINDOW_HEIGHT)
        
        # İkon ayarla
        try:
            icon_path = "assets/icons/guard_icon.ico"
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Pencereyi ortala
        self._center_window()
        
        # Stil ayarları
        self._setup_styles()
        
        # UI bileşenlerini oluştur
        self._create_widgets()
        
        # Callback'leri ayarla
        self._setup_callbacks()
        
        # Pencere kapatma olayı
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # İlk durumu ayarla
        self._update_stats()
    
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
        
        # Özel stiller
        style.configure('Header.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 12))
        style.configure('Success.TLabel', font=('Arial', 10), foreground='green')
        style.configure('Error.TLabel', font=('Arial', 10), foreground='red')
        style.configure('Warning.TLabel', font=('Arial', 10), foreground='orange')
        style.configure('Large.TButton', font=('Arial', 11, 'bold'), padding=8)
    
    def _create_widgets(self):
        """UI bileşenlerini oluşturur"""
        # Ana container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Üst panel - kullanıcı bilgisi ve kontroller
        self._create_top_panel(main_container)
        
        # Orta panel - video ve kontroller
        self._create_center_panel(main_container)
        
        # Alt panel - istatistikler ve durum
        self._create_bottom_panel(main_container)
    
    def _create_top_panel(self, parent):
        """Üst paneli oluşturur"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Sol taraf - kullanıcı bilgisi
        user_frame = ttk.Frame(top_frame)
        user_frame.pack(side=tk.LEFT)
        
        welcome_label = ttk.Label(
            user_frame,
            text=f"Hoş geldiniz, {self.user_data['name']}",
            style='Header.TLabel'
        )
        welcome_label.pack(anchor=tk.W)
        
        email_label = ttk.Label(
            user_frame,
            text=self.user_data['email'],
            font=('Arial', 10),
            foreground='gray'
        )
        email_label.pack(anchor=tk.W)
        
        # Sağ taraf - ana kontroller
        controls_frame = ttk.Frame(top_frame)
        controls_frame.pack(side=tk.RIGHT)
        
        # Ayarlar butonu
        settings_button = ttk.Button(
            controls_frame,
            text="⚙️ Ayarlar",
            command=self._open_settings
        )
        settings_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Çıkış butonu
        logout_button = ttk.Button(
            controls_frame,
            text="🚪 Çıkış",
            command=self._logout
        )
        logout_button.pack(side=tk.RIGHT, padx=(5, 0))
    
    def _create_center_panel(self, parent):
        """Orta paneli oluşturur"""
        center_frame = ttk.Frame(parent)
        center_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Sol taraf - video görüntüsü
        video_frame = ttk.LabelFrame(center_frame, text="Kamera Görüntüsü", padding="10")
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Video etiketi
        self.video_label = ttk.Label(video_frame, text="Kamera bağlantısı bekleniyor...", anchor=tk.CENTER)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Sağ taraf - kontroller ve durumlar
        control_frame = ttk.Frame(center_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Sistem kontrolleri
        self._create_system_controls(control_frame)
        
        # Durum paneli
        self._create_status_panel(control_frame)
        
        # Hızlı eylemler
        self._create_quick_actions(control_frame)
    
    def _create_system_controls(self, parent):
        """Sistem kontrollerini oluşturur"""
        controls_frame = ttk.LabelFrame(parent, text="Sistem Kontrolleri", padding="10")
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Kamera başlat/durdur
        self.start_button = ttk.Button(
            controls_frame,
            text="📹 Kamerayı Başlat",
            style='Large.TButton',
            command=self._toggle_camera
        )
        self.start_button.pack(fill=tk.X, pady=(0, 5))
        
        # Tespit başlat/durdur
        self.detection_button = ttk.Button(
            controls_frame,
            text="🔍 Tespiti Başlat",
            style='Large.TButton',
            command=self._toggle_detection,
            state='disabled'
        )
        self.detection_button.pack(fill=tk.X, pady=(0, 5))
        
        # Streaming başlat/durdur
        self.streaming_button = ttk.Button(
            controls_frame,
            text="📡 Canlı Yayın",
            command=self._toggle_streaming,
            state='disabled'
        )
        self.streaming_button.pack(fill=tk.X, pady=(0, 5))
        
        # Test bildirimi
        test_button = ttk.Button(
            controls_frame,
            text="🔔 Test Bildirimi",
            command=self._send_test_notification
        )
        test_button.pack(fill=tk.X)
    
    def _create_status_panel(self, parent):
        """Durum panelini oluşturur"""
        status_frame = ttk.LabelFrame(parent, text="Sistem Durumu", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Genel durum
        self.status_label = ttk.Label(
            status_frame,
            text="Sistem hazır",
            style='Status.TLabel'
        )
        self.status_label.pack(anchor=tk.W)
        
        # Tespit durumu
        self.detection_status_label = ttk.Label(
            status_frame,
            text="Tespit: Pasif",
            font=('Arial', 10),
            foreground='gray'
        )
        self.detection_status_label.pack(anchor=tk.W)
        
        # Streaming durumu
        self.streaming_status_label = ttk.Label(
            status_frame,
            text="Yayın: Kapalı",
            font=('Arial', 10),
            foreground='gray'
        )
        self.streaming_status_label.pack(anchor=tk.W)
    
    def _create_quick_actions(self, parent):
        """Hızlı eylem butonlarını oluşturur"""
        actions_frame = ttk.LabelFrame(parent, text="Hızlı Eylemler", padding="10")
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Ekran görüntüsü al
        screenshot_button = ttk.Button(
            actions_frame,
            text="📸 Ekran Görüntüsü",
            command=self._take_screenshot
        )
        screenshot_button.pack(fill=tk.X, pady=(0, 5))
        
        # Olayları görüntüle
        events_button = ttk.Button(
            actions_frame,
            text="📋 Olayları Görüntüle",
            command=self._show_events
        )
        events_button.pack(fill=tk.X, pady=(0, 5))
        
        # Stream URL'sini aç
        stream_url_button = ttk.Button(
            actions_frame,
            text="🌐 Stream URL",
            command=self._open_stream_url
        )
        stream_url_button.pack(fill=tk.X)
    
    def _create_bottom_panel(self, parent):
        """Alt paneli oluşturur"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.X)
        
        # İstatistikler
        self.stats_frame = ttk.LabelFrame(bottom_frame, text="İstatistikler", padding="10")
        self.stats_frame.pack(fill=tk.X)
        
        # İstatistik etiketleri (dinamik olarak oluşturulacak)
        self.stats_labels = {}
    
    def _setup_callbacks(self):
        """Callback fonksiyonlarını ayarlar"""
        # Kamera servisi callback'leri
        self.camera_service.set_callbacks(
            frame_callback=self._on_frame_received,
            detection_callback=self._on_detection_event,
            error_callback=self._on_camera_error
        )
    
    def _toggle_camera(self):
        """Kamerayı başlatır/durdurur"""
        try:
            if not self.is_camera_running.get():
                # Kamerayı başlat
                if self.camera_service.start_capture():
                    self.is_camera_running.set(True)
                    self.start_button.config(text="⏹️ Kamerayı Durdur")
                    self.detection_button.config(state='normal')
                    self.streaming_button.config(state='normal')
                    self._update_status("Kamera başlatıldı", "green")
                    
                    # Video güncelleme döngüsünü başlat
                    self._start_video_update()
                else:
                    messagebox.showerror("Hata", "Kamera başlatılamadı!")
            else:
                # Kamerayı durdur
                self.camera_service.stop_capture()
                self.is_camera_running.set(False)
                self.start_button.config(text="📹 Kamerayı Başlat")
                self.detection_button.config(state='disabled')
                self.streaming_button.config(state='disabled')
                
                # Tespiti de durdur
                if self.is_detection_active.get():
                    self._toggle_detection()
                
                # Streaming'i de durdur
                if self.is_streaming_active.get():
                    self._toggle_streaming()
                
                self._update_status("Kamera durduruldu", "orange")
                self._stop_video_update()
                
                # Video etiketi sıfırla
                self.video_label.config(image='', text="Kamera bağlantısı kesildi")
                
        except Exception as e:
            logging.error(f"Kamera toggle hatası: {str(e)}")
            messagebox.showerror("Hata", f"Kamera işlemi sırasında hata:\n{str(e)}")
    
    def _toggle_detection(self):
        """Düşme tespitini başlatır/durdurur"""
        try:
            if not self.is_detection_active.get():
                # Tespiti başlat
                if self.camera_service.start_detection():
                    self.is_detection_active.set(True)
                    self.detection_button.config(text="🛑 Tespiti Durdur")
                    self.detection_status_label.config(
                        text="Tespit: Aktif",
                        foreground='green'
                    )
                    self._update_status("Düşme tespiti aktif", "green")
                else:
                    messagebox.showerror("Hata", "Düşme tespiti başlatılamadı!")
            else:
                # Tespiti durdur
                self.camera_service.stop_detection()
                self.is_detection_active.set(False)
                self.detection_button.config(text="🔍 Tespiti Başlat")
                self.detection_status_label.config(
                    text="Tespit: Pasif",
                    foreground='gray'
                )
                self._update_status("Düşme tespiti durduruldu", "orange")
                
        except Exception as e:
            logging.error(f"Detection toggle hatası: {str(e)}")
            messagebox.showerror("Hata", f"Tespit işlemi sırasında hata:\n{str(e)}")
    
    def _toggle_streaming(self):
        """Canlı yayını başlatır/durdurur"""
        try:
            if not self.is_streaming_active.get():
                # Streaming'i başlat
                if initialize_streaming(self.user_id):
                    self.is_streaming_active.set(True)
                    self.streaming_button.config(text="📡 Yayını Durdur")
                    self.streaming_status_label.config(
                        text="Yayın: Aktif",
                        foreground='green'
                    )
                    
                    # Stream URL'sini göster
                    urls = self.streaming_service.get_stream_urls()
                    self._update_status(f"Canlı yayın başladı - IP: {urls['local_ip']}", "green")
                    
                    # Bilgi mesajı göster
                    messagebox.showinfo(
                        "Canlı Yayın Başladı",
                        f"Mobil uygulamadan bağlanmak için:\n\n"
                        f"IP Adresi: {urls['local_ip']}\n"
                        f"Port: {urls['port']}\n\n"
                        f"Stream URL: {urls['mjpeg_url']}"
                    )
                else:
                    messagebox.showerror("Hata", "Canlı yayın başlatılamadı!")
            else:
                # Streaming'i durdur
                self.streaming_service.stop_streaming()
                self.is_streaming_active.set(False)
                self.streaming_button.config(text="📡 Canlı Yayın")
                self.streaming_status_label.config(
                    text="Yayın: Kapalı",
                    foreground='gray'
                )
                self._update_status("Canlı yayın durduruldu", "orange")
                
        except Exception as e:
            logging.error(f"Streaming toggle hatası: {str(e)}")
            messagebox.showerror("Hata", f"Yayın işlemi sırasında hata:\n{str(e)}")
    
    def _send_test_notification(self):
        """Test bildirimi gönderir"""
        try:
            success = self.notification_service.send_test_notification(self.user_id)
            
            if success:
                messagebox.showinfo("Test Bildirimi", "Test bildirimi gönderildi!")
                self._update_status("Test bildirimi gönderildi", "green")
            else:
                messagebox.showerror("Hata", "Test bildirimi gönderilemedi!")
                
        except Exception as e:
            logging.error(f"Test bildirimi hatası: {str(e)}")
            messagebox.showerror("Hata", f"Test bildirimi sırasında hata:\n{str(e)}")
    
    def _take_screenshot(self):
        """Manuel ekran görüntüsü alır"""
        try:
            if not self.is_camera_running.get():
                messagebox.showwarning("Uyarı", "Ekran görüntüsü almak için kameranın açık olması gerekir!")
                return
            
            frame = self.camera_service.capture_screenshot()
            if frame is not None:
                # Dosya adı oluştur
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.jpg"
                
                # Kaydet
                cv2.imwrite(filename, frame)
                
                messagebox.showinfo("Başarılı", f"Ekran görüntüsü kaydedildi: {filename}")
                self._update_status("Ekran görüntüsü alındı", "green")
            else:
                messagebox.showerror("Hata", "Ekran görüntüsü alınamadı!")
                
        except Exception as e:
            logging.error(f"Screenshot hatası: {str(e)}")
            messagebox.showerror("Hata", f"Ekran görüntüsü alınırken hata:\n{str(e)}")
    
    def _show_events(self):
        """Olayları gösterir"""
        try:
            events = self.database_service.get_fall_events(self.user_id, limit=20)
            
            # Yeni pencere oluştur
            events_window = tk.Toplevel(self.root)
            events_window.title("Düşme Olayları")
            events_window.geometry("600x400")
            
            # Treeview oluştur
            tree_frame = ttk.Frame(events_window)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tree = ttk.Treeview(tree_frame, columns=('Date', 'Time', 'Confidence'), show='headings')
            tree.heading('#1', text='Tarih')
            tree.heading('#2', text='Saat')
            tree.heading('#3', text='Güven Oranı')
            
            # Scrollbar ekle
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Olayları ekle
            if events:
                for event in events:
                    timestamp = event.get('timestamp', event.get('created_at', 0))
                    date_str = time.strftime('%d/%m/%Y', time.localtime(timestamp))
                    time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
                    confidence = f"{event.get('confidence', 0):.1%}"
                    
                    tree.insert('', 'end', values=(date_str, time_str, confidence))
            else:
                tree.insert('', 'end', values=('Henüz olay yok', '', ''))
                
        except Exception as e:
            logging.error(f"Events görüntüleme hatası: {str(e)}")
            messagebox.showerror("Hata", f"Olaylar görüntülenirken hata:\n{str(e)}")
    
    def _open_stream_url(self):
        """Stream URL'sini tarayıcıda açar"""
        try:
            if not self.is_streaming_active.get():
                messagebox.showwarning("Uyarı", "Canlı yayının açık olması gerekir!")
                return
            
            urls = self.streaming_service.get_stream_urls()
            webbrowser.open(urls['mjpeg_url'])
            
        except Exception as e:
            logging.error(f"Stream URL açma hatası: {str(e)}")
            messagebox.showerror("Hata", f"Stream URL açılırken hata:\n{str(e)}")
    
    def _open_settings(self):
        """Ayarlar penceresini açar"""
        try:
            from ui.settings_window import SettingsWindow
            settings_window = SettingsWindow(self.root, self.user_data, self._on_settings_updated)
            
        except Exception as e:
            logging.error(f"Settings penceresi açma hatası: {str(e)}")
            messagebox.showerror("Hata", f"Ayarlar penceresi açılırken hata:\n{str(e)}")
    
    def _on_settings_updated(self):
        """Ayarlar güncellendiğinde çağrılır"""
        self._update_status("Ayarlar güncellendi", "green")
    
    def _logout(self):
        """Çıkış yapar"""
        response = messagebox.askyesno(
            "Çıkış",
            "Uygulamadan çıkmak istediğinize emin misiniz?"
        )
        
        if response:
            self._cleanup_and_close()
    
    def _start_video_update(self):
        """Video güncelleme döngüsünü başlatır"""
        self._update_video_frame()
    
    def _stop_video_update(self):
        """Video güncelleme döngüsünü durdurur"""
        if self.video_update_job:
            self.root.after_cancel(self.video_update_job)
            self.video_update_job = None
    
    def _update_video_frame(self):
        """Video frame'ini günceller"""
        try:
            if self.is_camera_running.get():
                frame = self.camera_service.get_processed_frame()
                
                if frame is not None:
                    # Frame'i tkinter için dönüştür
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Boyutları video label'a göre ayarla
                    label_width = self.video_label.winfo_width()
                    label_height = self.video_label.winfo_height()
                    
                    if label_width > 1 and label_height > 1:
                        # Oranı koruyarak yeniden boyutlandır
                        aspect_ratio = frame_rgb.shape[1] / frame_rgb.shape[0]
                        
                        if label_width / label_height > aspect_ratio:
                            new_height = label_height - 20
                            new_width = int(new_height * aspect_ratio)
                        else:
                            new_width = label_width - 20
                            new_height = int(new_width / aspect_ratio)
                        
                        frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                        
                        # PIL Image'e çevir
                        image = Image.fromarray(frame_resized)
                        photo = ImageTk.PhotoImage(image)
                        
                        # Label'ı güncelle
                        self.video_label.config(image=photo, text="")
                        self.video_label.image = photo  # Referansı sakla
                
                # Bir sonraki güncelleme için zamanlayıcı ayarla
                self.video_update_job = self.root.after(33, self._update_video_frame)  # ~30 FPS
                
        except Exception as e:
            logging.error(f"Video frame güncelleme hatası: {str(e)}")
    
    def _on_frame_received(self, frame):
        """Kameradan frame alındığında çağrılır"""
        # Bu fonksiyon kamera thread'inde çalışır
        # GUI güncellemeleri _update_video_frame'de yapılır
        pass
    
    def _on_detection_event(self, detection_result, processed_frame):
        """Düşme tespiti olayında çağrılır"""
        try:
            if detection_result["fall_detected"]:
                self.total_detections += 1
                self.last_detection_time = time.time()
                
                # Ana thread'de UI güncelle
                self.root.after(0, lambda: self._handle_detection_ui(detection_result))
                
        except Exception as e:
            logging.error(f"Detection event handling hatası: {str(e)}")
    
    def _handle_detection_ui(self, detection_result):
        """Ana thread'de tespit UI'sini günceller"""
        try:
            confidence = detection_result.get('confidence', 0)
            
            # Uyarı mesajı göster
            messagebox.showwarning(
                "DÜŞME TESPİT EDİLDİ!",
                f"Güven oranı: {confidence:.1%}\n\n"
                "Lütfen durumu kontrol edin!"
            )
            
            # Durum güncelle
            self._update_status(f"DÜŞME TESPİT EDİLDİ! Güven: {confidence:.1%}", "red")
            
            # İstatistikleri güncelle
            self._update_stats()
            
            # Streaming aktifse broadcast yap
            if self.is_streaming_active.get():
                self.streaming_service.broadcast_detection_event({
                    'confidence': confidence,
                    'timestamp': time.time(),
                    'user_id': self.user_id
                })
                
        except Exception as e:
            logging.error(f"Detection UI handling hatası: {str(e)}")
    
    def _on_camera_error(self, error_message):
        """Kamera hatası durumunda çağrılır"""
        logging.error(f"Kamera hatası: {error_message}")
        self.root.after(0, lambda: self._handle_camera_error(error_message))
    
    def _handle_camera_error(self, error_message):
        """Ana thread'de kamera hatasını işler"""
        self._update_status(f"Kamera hatası: {error_message}", "red")
        
        # Kamerayı kapat
        if self.is_camera_running.get():
            self._toggle_camera()
    
    def _update_status(self, message: str, color: str = "black"):
        """Durum mesajını günceller"""
        if self.status_label:
            self.status_label.config(text=message)
            
            # Renk ayarla
            if color == "green":
                self.status_label.config(style='Success.TLabel')
            elif color == "red":
                self.status_label.config(style='Error.TLabel')
            elif color == "orange":
                self.status_label.config(style='Warning.TLabel')
            else:
                self.status_label.config(style='Status.TLabel')
        
        logging.info(f"Status: {message}")
    
    def _update_stats(self):
        """İstatistikleri günceller"""
        try:
            # Veritabanından istatistikleri al
            stats = self.database_service.get_user_stats(self.user_id)
            
            # Streaming istatistikleri
            streaming_stats = self.streaming_service.get_streaming_stats()
            
            # Kamera bilgileri
            camera_info = self.camera_service.get_camera_info()
            
            # Session süresi
            session_duration = time.time() - self.session_start_time
            session_formatted = self._format_duration(session_duration)
            
            # Son tespit zamanı
            last_detection_str = "Hiç tespit edilmedi"
            if self.last_detection_time:
                last_detection_str = time.strftime('%H:%M:%S', time.localtime(self.last_detection_time))
            
            # İstatistik verilerini hazırla
            stat_data = [
                ("Toplam Olay", stats.get('total_events', 0)),
                ("Bugün", stats.get('events_today', 0)),
                ("Bu Hafta", stats.get('events_this_week', 0)),
                ("Session Süre", session_formatted),
                ("Son Tespit", last_detection_str),
                ("Bağlı İstemci", streaming_stats.get('connected_clients', 0)),
                ("Kamera FPS", f"{camera_info.get('current_fps', 0):.1f}")
            ]
            
            # Mevcut etiketleri temizle
            for widget in self.stats_frame.winfo_children():
                widget.destroy()
            
            # Yeni etiketleri oluştur
            for i, (label, value) in enumerate(stat_data):
                row = i // 3
                col = i % 3
                
                stat_frame = ttk.Frame(self.stats_frame)
                stat_frame.grid(row=row, column=col, padx=10, pady=5, sticky='w')
                
                ttk.Label(stat_frame, text=f"{label}:", font=('Arial', 9, 'bold')).pack(anchor='w')
                ttk.Label(stat_frame, text=str(value), font=('Arial', 9)).pack(anchor='w')
            
            # Bir sonraki güncelleme için zamanlayıcı
            self.stats_update_job = self.root.after(5000, self._update_stats)  # 5 saniyede bir
            
        except Exception as e:
            logging.error(f"Stats güncelleme hatası: {str(e)}")
    
    def _format_duration(self, seconds):
        """Süreyi okunabilir formata çevirir"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def _on_window_close(self):
        """Pencere kapatma olayını işler"""
        response = messagebox.askyesno(
            "Çıkış",
            "Uygulamayı kapatmak istediğinize emin misiniz?\n\n"
            "Tüm aktif servisler durdurulacak."
        )
        
        if response:
            self._cleanup_and_close()
    
    def _cleanup_and_close(self):
        """Kaynakları temizler ve pencereyi kapatır"""
        try:
            logging.info("Ana pencere kapatılıyor, kaynaklar temizleniyor...")
            
            # Update job'ları iptal et
            if self.video_update_job:
                self.root.after_cancel(self.video_update_job)
            if self.stats_update_job:
                self.root.after_cancel(self.stats_update_job)
            
            # Servisleri durdur
            if self.is_detection_active.get():
                self.camera_service.stop_detection()
            
            if self.is_camera_running.get():
                self.camera_service.stop_capture()
            
            if self.is_streaming_active.get():
                self.streaming_service.stop_streaming()
            
            # Pencereyi kapat
            self.root.quit()
            
        except Exception as e:
            logging.error(f"Cleanup sırasında hata: {str(e)}")
            self.root.quit()
    
    def run(self):
        """Pencereyi çalıştırır"""
        try:
            self.create_window()
            
            logging.info(f"Ana pencere başlatılıyor - Kullanıcı: {self.user_data['email']}")
            
            # İstatistik güncellemesini başlat
            self._update_stats()
            
            self.root.mainloop()
            
        except Exception as e:
            logging.error(f"Ana pencere çalışırken hata: {str(e)}")
            raise e
        finally:
            try:
                self.root.destroy()
            except:
                pass

# Test fonksiyonu
def test_main_window():
    """Ana pencereyi test eder"""
    try:
        logging.basicConfig(level=logging.INFO)
        
        # Dummy kullanıcı verisi
        test_user = {
            'uid': 'test_user',
            'email': 'test@example.com',
            'name': 'Test Kullanıcı'
        }
        
        main_window = MainWindow(test_user)
        main_window.run()
        
    except Exception as e:
        logging.error(f"Test sırasında hata: {str(e)}")

if __name__ == "__main__":