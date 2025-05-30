# =======================================================================================
# 📄 Dosya Adı   : styles.py
# 📁 Konum       : guard_pc/ui/styles.py
# 📌 Açıklama    : Guard PC uygulaması UI stil tanımları
#                 - Renk paletleri
#                 - Font ayarları
#                 - Tema yapılandırmaları
#                 - Özel stil sınıfları
#
# 🔗 Bağlantılı Dosyalar:
#   - config/settings.py       : Tema ayarları
#   - ui/login_window.py       : Login penceresi stilleri
#   - ui/main_window.py        : Ana pencere stilleri
#   - ui/settings_window.py    : Ayarlar penceresi stilleri
# =======================================================================================

import tkinter as tk
from tkinter import ttk
import logging
from config.settings import Settings

class GuardStyles:
    """Guard uygulaması için stil tanımları"""
    
    # Renk paletleri
    COLORS = {
        'primary': '#2196F3',           # Ana mavi
        'primary_dark': '#1976D2',      # Koyu mavi
        'primary_light': '#BBDEFB',     # Açık mavi
        
        'secondary': '#4CAF50',         # Yeşil (başarı)
        'secondary_dark': '#388E3C',    # Koyu yeşil
        'secondary_light': '#C8E6C9',   # Açık yeşil
        
        'warning': '#FF9800',           # Turuncu (uyarı)
        'warning_dark': '#F57C00',      # Koyu turuncu
        'warning_light': '#FFE0B2',     # Açık turuncu
        
        'error': '#F44336',             # Kırmızı (hata)
        'error_dark': '#D32F2F',        # Koyu kırmızı
        'error_light': '#FFCDD2',       # Açık kırmızı
        
        'background': '#FFFFFF',        # Beyaz arka plan
        'background_dark': '#F5F5F5',   # Gri arka plan
        'surface': '#FAFAFA',           # Yüzey rengi
        
        'text_primary': '#212121',      # Ana metin
        'text_secondary': '#757575',    # İkincil metin
        'text_disabled': '#BDBDBD',     # Pasif metin
        
        'border': '#E0E0E0',            # Kenarlık
        'border_dark': '#BDBDBD',       # Koyu kenarlık
        
        'shadow': '#00000020'           # Gölge (alpha)
    }
    
    # Dark mode renkleri
    DARK_COLORS = {
        'primary': '#1E88E5',
        'primary_dark': '#1565C0',
        'primary_light': '#2196F3',
        
        'secondary': '#4CAF50',
        'secondary_dark': '#388E3C',
        'secondary_light': '#66BB6A',
        
        'warning': '#FF9800',
        'warning_dark': '#F57C00',
        'warning_light': '#FFB74D',
        
        'error': '#F44336',
        'error_dark': '#D32F2F',
        'error_light': '#EF5350',
        
        'background': '#121212',        # Koyu arka plan
        'background_dark': '#1E1E1E',   # Daha koyu arka plan
        'surface': '#1E1E1E',           # Yüzey rengi
        
        'text_primary': '#FFFFFF',      # Beyaz metin
        'text_secondary': '#AAAAAA',    # Gri metin
        'text_disabled': '#666666',     # Pasif metin
        
        'border': '#333333',            # Koyu kenarlık
        'border_dark': '#444444',       # Daha koyu kenarlık
        
        'shadow': '#00000040'           # Koyu gölge
    }
    
    # Font ayarları
    FONTS = {
        'default': ('Segoe UI', 9),
        'small': ('Segoe UI', 8),
        'medium': ('Segoe UI', 10),
        'large': ('Segoe UI', 12),
        'xlarge': ('Segoe UI', 14),
        'xxlarge': ('Segoe UI', 16),
        
        'title': ('Segoe UI', 18, 'bold'),
        'heading': ('Segoe UI', 14, 'bold'),
        'subheading': ('Segoe UI', 12, 'bold'),
        'button': ('Segoe UI', 10, 'bold'),
        
        'monospace': ('Consolas', 9),
        'monospace_small': ('Consolas', 8),
        'monospace_large': ('Consolas', 12)
    }
    
    # Boyutlar ve padding
    DIMENSIONS = {
        'padding_small': 5,
        'padding_medium': 10,
        'padding_large': 15,
        'padding_xlarge': 20,
        
        'margin_small': 5,
        'margin_medium': 10,
        'margin_large': 15,
        
        'border_width': 1,
        'border_radius': 5,
        
        'button_height': 32,
        'button_width': 100,
        'button_padding': 8,
        
        'entry_height': 24,
        'label_height': 20,
        
        'icon_small': 16,
        'icon_medium': 24,
        'icon_large': 32,
        'icon_xlarge': 48
    }

class StyleManager:
    """Stil yöneticisi sınıfı"""
    
    def __init__(self):
        """Stil yöneticisini başlatır"""
        self.current_theme = Settings.THEME_MODE
        self.style = None
        self.colors = self._get_color_scheme()
        
        logging.info(f"StyleManager başlatıldı - Tema: {self.current_theme}")
    
    def _get_color_scheme(self):
        """Mevcut temaya göre renk şemasını döndürür"""
        if self.current_theme == "dark":
            return GuardStyles.DARK_COLORS
        else:
            return GuardStyles.COLORS
    
    def setup_styles(self, root):
        """Ana pencere için stilleri ayarlar"""
        try:
            self.style = ttk.Style(root)
            
            # Tema seçimi
            self._configure_theme()
            
            # Özel stilleri tanımla
            self._define_custom_styles()
            
            logging.info("Stiller başarıyla ayarlandı")
            
        except Exception as e:
            logging.error(f"Stil ayarlama hatası: {str(e)}")
    
    def _configure_theme(self):
        """Temel temayı yapılandırır"""
        try:
            # Mevcut temaları listele
            available_themes = self.style.theme_names()
            
            # Tema seçimi
            if self.current_theme == "dark":
                if 'equilux' in available_themes:
                    self.style.theme_use('equilux')
                elif 'clam' in available_themes:
                    self.style.theme_use('clam')
                else:
                    self.style.theme_use('default')
            else:
                if 'vista' in available_themes:
                    self.style.theme_use('vista')
                elif 'clam' in available_themes:
                    self.style.theme_use('clam')
                else:
                    self.style.theme_use('default')
                    
            logging.info(f"Tema ayarlandı: {self.style.theme_use()}")
            
        except Exception as e:
            logging.warning(f"Tema ayarlama hatası: {str(e)}")
            self.style.theme_use('default')
    
    def _define_custom_styles(self):
        """Özel stilleri tanımlar"""
        try:
            # Başlık stilleri
            self.style.configure(
                'Title.TLabel',
                font=GuardStyles.FONTS['title'],
                foreground=self.colors['text_primary']
            )
            
            self.style.configure(
                'Heading.TLabel',
                font=GuardStyles.FONTS['heading'],
                foreground=self.colors['text_primary']
            )
            
            self.style.configure(
                'Subheading.TLabel',
                font=GuardStyles.FONTS['subheading'],
                foreground=self.colors['text_primary']
            )
            
            # Durum stilleri
            self.style.configure(
                'Success.TLabel',
                font=GuardStyles.FONTS['medium'],
                foreground=self.colors['secondary']
            )
            
            self.style.configure(
                'Warning.TLabel',
                font=GuardStyles.FONTS['medium'],
                foreground=self.colors['warning']
            )
            
            self.style.configure(
                'Error.TLabel',
                font=GuardStyles.FONTS['medium'],
                foreground=self.colors['error']
            )
            
            self.style.configure(
                'Info.TLabel',
                font=GuardStyles.FONTS['medium'],
                foreground=self.colors['primary']
            )
            
            # Buton stilleri
            self.style.configure(
                'Large.TButton',
                font=GuardStyles.FONTS['button'],
                padding=GuardStyles.DIMENSIONS['button_padding']
            )
            
            self.style.configure(
                'Primary.TButton',
                font=GuardStyles.FONTS['button'],
                padding=GuardStyles.DIMENSIONS['button_padding']
            )
            
            self.style.configure(
                'Success.TButton',
                font=GuardStyles.FONTS['button'],
                padding=GuardStyles.DIMENSIONS['button_padding']
            )
            
            self.style.configure(
                'Warning.TButton',
                font=GuardStyles.FONTS['button'],
                padding=GuardStyles.DIMENSIONS['button_padding']
            )
            
            self.style.configure(
                'Danger.TButton',
                font=GuardStyles.FONTS['button'],
                padding=GuardStyles.DIMENSIONS['button_padding']
            )
            
            # Frame stilleri
            self.style.configure(
                'Card.TFrame',
                relief='solid',
                borderwidth=1
            )
            
            # Entry stilleri
            self.style.configure(
                'Large.TEntry',
                font=GuardStyles.FONTS['medium'],
                fieldbackground=self.colors['background']
            )
            
            # Notebook stilleri
            self.style.configure(
                'TNotebook',
                background=self.colors['background']
            )
            
            self.style.configure(
                'TNotebook.Tab',
                font=GuardStyles.FONTS['medium'],
                padding=[GuardStyles.DIMENSIONS['padding_medium'], 
                        GuardStyles.DIMENSIONS['padding_small']]
            )
            
            # Progressbar stilleri
            self.style.configure(
                'TProgressbar',
                background=self.colors['primary'],
                troughcolor=self.colors['background_dark']
            )
            
            # LabelFrame stilleri
            self.style.configure(
                'TLabelframe',
                background=self.colors['background'],
                relief='solid',
                borderwidth=1
            )
            
            self.style.configure(
                'TLabelframe.Label',
                font=GuardStyles.FONTS['subheading'],
                foreground=self.colors['text_primary']
            )
            
            # Scale stilleri
            self.style.configure(
                'TScale',
                background=self.colors['primary'],
                troughcolor=self.colors['background_dark']
            )
            
            # Checkbutton stilleri
            self.style.configure(
                'TCheckbutton',
                font=GuardStyles.FONTS['medium'],
                foreground=self.colors['text_primary']
            )
            
            # Radiobutton stilleri
            self.style.configure(
                'TRadiobutton',
                font=GuardStyles.FONTS['medium'],
                foreground=self.colors['text_primary']
            )
            
            # Treeview stilleri
            self.style.configure(
                'Treeview',
                font=GuardStyles.FONTS['default'],
                background=self.colors['background'],
                foreground=self.colors['text_primary'],
                fieldbackground=self.colors['background']
            )
            
            self.style.configure(
                'Treeview.Heading',
                font=GuardStyles.FONTS['subheading'],
                background=self.colors['background_dark'],
                foreground=self.colors['text_primary']
            )
            
        except Exception as e:
            logging.error(f"Özel stil tanımlama hatası: {str(e)}")
    
    def get_color(self, color_name: str) -> str:
        """Renk kodunu döndürür"""
        return self.colors.get(color_name, '#000000')
    
    def get_font(self, font_name: str) -> tuple:
        """Font bilgisini döndürür"""
        return GuardStyles.FONTS.get(font_name, GuardStyles.FONTS['default'])
    
    def get_dimension(self, dimension_name: str) -> int:
        """Boyut değerini döndürür"""
        return GuardStyles.DIMENSIONS.get(dimension_name, 10)
    
    def apply_button_style(self, button, style_type: str = 'default'):
        """Butona özel stil uygular"""
        try:
            style_configs = {
                'primary': {
                    'style': 'Primary.TButton'
                },
                'success': {
                    'style': 'Success.TButton'
                },
                'warning': {
                    'style': 'Warning.TButton'
                },
                'danger': {
                    'style': 'Danger.TButton'
                },
                'large': {
                    'style': 'Large.TButton'
                }
            }
            
            config = style_configs.get(style_type, {})
            if 'style' in config:
                button.configure(style=config['style'])
                
        except Exception as e:
            logging.error(f"Buton stil uygulama hatası: {str(e)}")
    
    def apply_label_style(self, label, style_type: str = 'default'):
        """Etikete özel stil uygular"""
        try:
            style_configs = {
                'title': {
                    'style': 'Title.TLabel'
                },
                'heading': {
                    'style': 'Heading.TLabel'
                },
                'subheading': {
                    'style': 'Subheading.TLabel'
                },
                'success': {
                    'style': 'Success.TLabel'
                },
                'warning': {
                    'style': 'Warning.TLabel'
                },
                'error': {
                    'style': 'Error.TLabel'
                },
                'info': {
                    'style': 'Info.TLabel'
                }
            }
            
            config = style_configs.get(style_type, {})
            if 'style' in config:
                label.configure(style=config['style'])
                
        except Exception as e:
            logging.error(f"Etiket stil uygulama hatası: {str(e)}")
    
    def create_card_frame(self, parent, **kwargs):
        """Kart görünümünde frame oluşturur"""
        try:
            frame = ttk.Frame(parent, style='Card.TFrame', **kwargs)
            return frame
        except Exception as e:
            logging.error(f"Card frame oluşturma hatası: {str(e)}")
            return ttk.Frame(parent, **kwargs)
    
    def update_theme(self, new_theme: str):
        """Temayı değiştirir"""
        try:
            self.current_theme = new_theme
            self.colors = self._get_color_scheme()
            
            if self.style:
                self._configure_theme()
                self._define_custom_styles()
            
            logging.info(f"Tema güncellendi: {new_theme}")
            
        except Exception as e:
            logging.error(f"Tema güncelleme hatası: {str(e)}")

# Global stil yöneticisi
_style_manager = None

def get_style_manager():
    """Global stil yöneticisini döndürür"""
    global _style_manager
    if _style_manager is None:
        _style_manager = StyleManager()
    return _style_manager

def setup_window_styles(root):
    """Pencere için stilleri ayarlar"""
    style_manager = get_style_manager()
    style_manager.setup_styles(root)
    return style_manager

def apply_guard_theme(root):
    """Guard temasını uygular"""
    try:
        style_manager = setup_window_styles(root)
        
        # Ana pencere arka plan rengi
        root.configure(bg=style_manager.get_color('background'))
        
        return style_manager
        
    except Exception as e:
        logging.error(f"Guard tema uygulama hatası: {str(e)}")
        return None

# Yardımcı fonksiyonlar
def get_icon_font():
    """İkon fontu döndürür"""
    return ('Segoe UI Symbol', 12)

def get_emoji_font():
    """Emoji fontu döndürür"""
    return ('Segoe UI Emoji', 12)

def create_tooltip_style():
    """Tooltip stili oluşturur"""
    return {
        'font': GuardStyles.FONTS['small'],
        'bg': GuardStyles.COLORS['background_dark'],
        'fg': GuardStyles.COLORS['text_primary'],
        'relief': 'solid',
        'borderwidth': 1
    }

# CSS benzeri yardımcı sınıf
class CSSHelper:
    """CSS benzeri stil yardımcıları"""
    
    @staticmethod
    def padding(top=0, right=None, bottom=None, left=None):
        """CSS padding benzeri"""
        if right is None:
            right = top
        if bottom is None:
            bottom = top
        if left is None:
            left = right
        
        return {
            'padx': (left, right),
            'pady': (top, bottom)
        }
    
    @staticmethod
    def margin(top=0, right=None, bottom=None, left=None):
        """CSS margin benzeri"""
        if right is None:
            right = top
        if bottom is None:
            bottom = top
        if left is None:
            left = right
        
        return {
            'padx': (left, right),
            'pady': (top, bottom)
        }

# Test fonksiyonu
def test_styles():
    """Stilleri test eder"""
    try:
        root = tk.Tk()
        root.title("Guard Styles Test")
        root.geometry("600x400")
        
        # Stilleri uygula
        style_manager = apply_guard_theme(root)
        
        # Test widget'ları
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title = ttk.Label(main_frame, text="Guard Styles Test")
        style_manager.apply_label_style(title, 'title')
        title.pack(pady=(0, 20))
        
        # Butonlar
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        buttons = [
            ("Primary", "primary"),
            ("Success", "success"),
            ("Warning", "warning"),
            ("Danger", "danger")
        ]
        
        for text, style_type in buttons:
            btn = ttk.Button(button_frame, text=text)
            style_manager.apply_button_style(btn, style_type)
            btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Etiketler
        label_frame = ttk.Frame(main_frame)
        label_frame.pack(fill=tk.X, pady=(0, 20))
        
        labels = [
            ("Success Label", "success"),
            ("Warning Label", "warning"),
            ("Error Label", "error"),
            ("Info Label", "info")
        ]
        
        for text, style_type in labels:
            lbl = ttk.Label(label_frame, text=text)
            style_manager.apply_label_style(lbl, style_type)
            lbl.pack(anchor=tk.W, pady=2)
        
        root.mainloop()
        
    except Exception as e:
        logging.error(f"Stil testi hatası: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_styles()