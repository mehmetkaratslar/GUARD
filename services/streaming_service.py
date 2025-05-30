# =======================================================================================
# 📄 Dosya Adı   : streaming_service.py
# 📁 Konum       : guard_pc/services/streaming_service.py
# 📌 Açıklama    : Mobil uygulamalar için canlı video yayını
#                 - HTTP MJPEG streaming
#                 - WebSocket bağlantısı
#                 - Düşük gecikme optimizasyonu
#                 - Çoklu istemci desteği
#
# 🔗 Bağlantılı Dosyalar:
#   - services/camera_service.py : Kamera görüntülerini alır
#   - config/settings.py        : Streaming ayarları
#   - Flask web server          : HTTP streaming endpoint'leri
# =======================================================================================

import logging
import threading
import time
import cv2
import socket
from typing import Set, Optional, Dict
from flask import Flask, Response, jsonify, request
from flask_socketio import SocketIO, emit
import base64
import json
from datetime import datetime

from config.settings import Settings
from services.camera_service import get_camera_service
from services.database_service import get_database_service

class StreamingService:
    """Canlı video yayın servisi"""
    
    def __init__(self):
        """Streaming servisini başlatır"""
        self.camera_service = get_camera_service()
        self.database_service = get_database_service()
        
        # Flask uygulaması
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'guard_streaming_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Streaming ayarları
        self.host = Settings.STREAMING_HOST
        self.port = Settings.STREAMING_PORT
        
        # Bağlı istemciler
        self.connected_clients: Set[str] = set()
        self.client_info: Dict[str, Dict] = {}
        
        # Streaming durumu
        self.is_streaming = False
        self.stream_thread = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # İstatistikler
        self.total_connections = 0
        self.bytes_sent = 0
        self.start_time = time.time()
        
        self._setup_routes()
        self._setup_socketio_events()
        
        logging.info("StreamingService başlatıldı")
    
    def _setup_routes(self):
        """Flask route'larını ayarlar"""
        
        @self.app.route('/stream')
        def video_stream():
            """MJPEG video stream endpoint'i"""
            return Response(
                self._generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/stream_info')
        def stream_info():
            """Stream bilgilerini döndürür"""
            return jsonify({
                'status': 'active' if self.is_streaming else 'inactive',
                'connected_clients': len(self.connected_clients),
                'total_connections': self.total_connections,
                'bytes_sent': self.bytes_sent,
                'uptime': time.time() - self.start_time,
                'camera_info': self.camera_service.get_camera_info()
            })
        
        @self.app.route('/api/events')
        def get_events():
            """Son olayları döndürür"""
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'user_id gerekli'}), 400
            
            limit = int(request.args.get('limit', 10))
            events = self.database_service.get_fall_events(user_id, limit)
            
            return jsonify({
                'events': events,
                'count': len(events)
            })
        
        @self.app.route('/api/stats')
        def get_stats():
            """Kullanıcı istatistiklerini döndürür"""
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'user_id gerekli'}), 400
            
            stats = self.database_service.get_user_stats(user_id)
            return jsonify(stats)
    
    def _setup_socketio_events(self):
        """WebSocket event'lerini ayarlar"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            self.connected_clients.add(client_id)
            self.total_connections += 1
            
            client_info = {
                'connected_at': time.time(),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
            self.client_info[client_id] = client_info
            
            logging.info(f"İstemci bağlandı: {client_id} - IP: {client_info['ip']}")
            
            emit('connection_status', {
                'status': 'connected',
                'client_id': client_id,
                'server_time': time.time()
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            if client_id in self.connected_clients:
                self.connected_clients.remove(client_id)
            
            if client_id in self.client_info:
                del self.client_info[client_id]
            
            logging.info(f"İstemci bağlantısı kesildi: {client_id}")
        
        @self.socketio.on('request_frame')
        def handle_frame_request():
            """İstemci frame talep ettiğinde"""
            if self.current_frame is not None:
                self._send_frame_to_client(request.sid)
        
        @self.socketio.on('client_info')
        def handle_client_info(data):
            """İstemci bilgilerini günceller"""
            client_id = request.sid
            if client_id in self.client_info:
                self.client_info[client_id].update(data)
                logging.info(f"İstemci bilgileri güncellendi: {client_id}")
    
    def start_streaming(self, user_id: str = None) -> bool:
        """Streaming'i başlatır"""
        try:
            if self.is_streaming:
                logging.warning("Streaming zaten aktif")
                return True
            
            # Kamera servisinin aktif olduğunu kontrol et
            if not self.camera_service.is_running:
                logging.error("Kamera servisi aktif değil")
                return False
            
            self.is_streaming = True
            
            # Frame günceleme thread'ini başlat
            self.stream_thread = threading.Thread(target=self._frame_update_loop, daemon=True)
            self.stream_thread.start()
            
            # Flask sunucusunu başlat (ayrı thread'de)
            server_thread = threading.Thread(
                target=self._run_flask_server,
                daemon=True
            )
            server_thread.start()
            
            logging.info(f"Streaming başlatıldı - Port: {self.port}")
            return True
            
        except Exception as e:
            logging.error(f"Streaming başlatılırken hata: {str(e)}")
            return False
    
    def stop_streaming(self):
        """Streaming'i durdurur"""
        try:
            if not self.is_streaming:
                return
            
            logging.info("Streaming durduruluyor...")
            self.is_streaming = False
            
            # Tüm istemcilere kapatma bildirimi gönder
            self.socketio.emit('stream_stopped', {
                'message': 'Stream durduruldu',
                'timestamp': time.time()
            })
            
            # Thread'in bitmesini bekle
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=2.0)
            
            logging.info("Streaming durduruldu")
            
        except Exception as e:
            logging.error(f"Streaming durdurulurken hata: {str(e)}")
    
    def _frame_update_loop(self):
        """Frame güncelleme döngüsü"""
        try:
            while self.is_streaming:
                # Kameradan en son frame'i al
                frame = self.camera_service.get_processed_frame()
                
                if frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    
                    # WebSocket üzerinden frame gönder
                    if self.connected_clients:
                        self._broadcast_frame()
                
                time.sleep(1.0 / 30)  # 30 FPS hedefi
                
        except Exception as e:
            logging.error(f"Frame update loop hatası: {str(e)}")
    
    def _generate_frames(self):
        """MJPEG stream için frame generator"""
        try:
            while self.is_streaming:
                with self.frame_lock:
                    if self.current_frame is None:
                        time.sleep(0.1)
                        continue
                    
                    frame = self.current_frame.copy()
                
                # Frame'i JPEG'e encode et
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                if ret:
                    frame_bytes = buffer.tobytes()
                    self.bytes_sent += len(frame_bytes)
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            logging.error(f"Frame generation hatası: {str(e)}")
    
    def _broadcast_frame(self):
        """Tüm bağlı istemcilere frame gönderir"""
        try:
            if not self.current_frame is not None or not self.connected_clients:
                return
            
            # Frame'i base64'e encode et
            ret, buffer = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            
            if ret:
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                frame_data = {
                    'frame': frame_base64,
                    'timestamp': time.time(),
                    'format': 'jpeg'
                }
                
                self.socketio.emit('video_frame', frame_data)
                
        except Exception as e:
            logging.error(f"Frame broadcast hatası: {str(e)}")
    
    def _send_frame_to_client(self, client_id: str):
        """Belirli bir istemciye frame gönderir"""
        try:
            if self.current_frame is None:
                return
            
            # Frame'i base64'e encode et
            ret, buffer = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            
            if ret:
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                frame_data = {
                    'frame': frame_base64,
                    'timestamp': time.time(),
                    'format': 'jpeg'
                }
                
                self.socketio.emit('video_frame', frame_data, room=client_id)
                
        except Exception as e:
            logging.error(f"Frame gönderiminde hata: {str(e)}")
    
    def _run_flask_server(self):
        """Flask sunucusunu çalıştırır"""
        try:
            # Port kontrolü
            if not self._is_port_available(self.port):
                logging.error(f"Port {self.port} kullanımda")
                return
            
            logging.info(f"Flask sunucusu başlatılıyor - {self.host}:{self.port}")
            
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                log_output=False
            )
            
        except Exception as e:
            logging.error(f"Flask sunucusu çalıştırılırken hata: {str(e)}")
    
    def _is_port_available(self, port: int) -> bool:
        """Port'un kullanılabilir olup olmadığını kontrol eder"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
            return True
        except OSError:
            return False
    
    def get_local_ip(self) -> str:
        """Yerel IP adresini döndürür"""
        try:
            # Google DNS'e bağlanarak yerel IP'yi öğren
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def get_stream_urls(self) -> Dict[str, str]:
        """Stream URL'lerini döndürür"""
        local_ip = self.get_local_ip()
        
        return {
            "mjpeg_url": f"http://{local_ip}:{self.port}/stream",
            "websocket_url": f"ws://{local_ip}:{self.port}",
            "api_base_url": f"http://{local_ip}:{self.port}/api",
            "local_ip": local_ip,
            "port": self.port
        }
    
    def broadcast_detection_event(self, event_data: Dict):
        """Düşme tespiti olayını tüm istemcilere gönderir"""
        try:
            if not self.connected_clients:
                return
            
            detection_message = {
                "type": "fall_detection",
                "event": event_data,
                "timestamp": time.time(),
                "severity": "critical"
            }
            
            self.socketio.emit('detection_alert', detection_message)
            logging.info(f"Düşme tespiti {len(self.connected_clients)} istemciye gönderildi")
            
        except Exception as e:
            logging.error(f"Detection event broadcast hatası: {str(e)}")
    
    def send_system_status(self):
        """Sistem durumu bilgilerini gönderir"""
        try:
            if not self.connected_clients:
                return
            
            camera_info = self.camera_service.get_camera_info()
            
            status_data = {
                "type": "system_status",
                "camera": camera_info,
                "streaming": {
                    "active": self.is_streaming,
                    "connected_clients": len(self.connected_clients),
                    "bytes_sent": self.bytes_sent,
                    "uptime": time.time() - self.start_time
                },
                "timestamp": time.time()
            }
            
            self.socketio.emit('system_status', status_data)
            
        except Exception as e:
            logging.error(f"System status gönderimi hatası: {str(e)}")
    
    def get_streaming_stats(self) -> Dict:
        """Streaming istatistiklerini döndürür"""
        try:
            uptime = time.time() - self.start_time
            
            return {
                "is_streaming": self.is_streaming,
                "connected_clients": len(self.connected_clients),
                "total_connections": self.total_connections,
                "bytes_sent": self.bytes_sent,
                "bytes_sent_mb": self.bytes_sent / (1024 * 1024),
                "uptime_seconds": uptime,
                "uptime_formatted": self._format_uptime(uptime),
                "average_bandwidth": self.bytes_sent / uptime if uptime > 0 else 0,
                "client_info": dict(self.client_info),
                "urls": self.get_stream_urls()
            }
            
        except Exception as e:
            logging.error(f"Streaming istatistikleri alınırken hata: {str(e)}")
            return {}
    
    def _format_uptime(self, seconds: float) -> str:
        """Uptime'ı okunabilir formata çevirir"""
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hours > 0:
                return f"{hours}sa {minutes}dk {secs}sn"
            elif minutes > 0:
                return f"{minutes}dk {secs}sn"
            else:
                return f"{secs}sn"
                
        except Exception:
            return "Bilinmiyor"
    
    def save_stream_info_to_database(self, user_id: str):
        """Stream bilgilerini veritabanına kaydeder (mobil uygulama için)"""
        try:
            stream_info = {
                "stream_urls": self.get_stream_urls(),
                "last_updated": time.time(),
                "status": "active" if self.is_streaming else "inactive"
            }
            
            # Kullanıcı ayarlarına stream bilgilerini ekle
            settings_update = {
                "stream_info": stream_info
            }
            
            success = self.database_service.save_user_settings(user_id, settings_update)
            
            if success:
                logging.info(f"Stream bilgileri veritabanına kaydedildi - User: {user_id}")
            
            return success
            
        except Exception as e:
            logging.error(f"Stream bilgileri kaydedilirken hata: {str(e)}")
            return False
    
    def cleanup(self):
        """Kaynakları temizler"""
        try:
            self.stop_streaming()
            
            # Tüm bağlantıları kapat
            for client_id in list(self.connected_clients):
                self.socketio.disconnect(client_id)
            
            self.connected_clients.clear()
            self.client_info.clear()
            
            logging.info("StreamingService temizlendi")
            
        except Exception as e:
            logging.error(f"Streaming cleanup hatası: {str(e)}")

class RTSPServer:
    """RTSP sunucusu (gelişmiş streaming için)"""
    
    def __init__(self, port: int = None):
        """RTSP sunucusunu başlatır"""
        self.port = port or Settings.RTSP_PORT
        self.is_running = False
        self.server_thread = None
        
        logging.info(f"RTSPServer oluşturuldu - Port: {self.port}")
    
    def start_server(self) -> bool:
        """RTSP sunucusunu başlatır"""
        try:
            if self.is_running:
                return True
            
            # Basit RTSP implementasyonu buraya eklenebilir
            # Şu an için sadece HTTP streaming kullanıyoruz
            
            logging.info("RTSP sunucusu başlatıldı (placeholder)")
            self.is_running = True
            return True
            
        except Exception as e:
            logging.error(f"RTSP sunucusu başlatılırken hata: {str(e)}")
            return False
    
    def stop_server(self):
        """RTSP sunucusunu durdurur"""
        try:
            if not self.is_running:
                return
            
            self.is_running = False
            logging.info("RTSP sunucusu durduruldu")
            
        except Exception as e:
            logging.error(f"RTSP sunucusu durdurulurken hata: {str(e)}")

# Global streaming service instance'ı
_streaming_service_instance = None
_rtsp_server_instance = None

def get_streaming_service() -> StreamingService:
    """Global StreamingService instance'ını döndürür"""
    global _streaming_service_instance
    if _streaming_service_instance is None:
        _streaming_service_instance = StreamingService()
    return _streaming_service_instance

def get_rtsp_server() -> RTSPServer:
    """Global RTSPServer instance'ını döndürür"""
    global _rtsp_server_instance
    if _rtsp_server_instance is None:
        _rtsp_server_instance = RTSPServer()
    return _rtsp_server_instance

def initialize_streaming(user_id: str) -> bool:
    """Streaming servislerini kullanıcı için başlatır"""
    try:
        streaming_service = get_streaming_service()
        success = streaming_service.start_streaming(user_id)
        
        if success:
            # Stream bilgilerini veritabanına kaydet
            streaming_service.save_stream_info_to_database(user_id)
        
        return success
        
    except Exception as e:
        logging.error(f"Streaming başlatılırken hata: {str(e)}")
        return False