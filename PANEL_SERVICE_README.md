# Web Panel Ubuntu Servisi Kurulumu

Bu klasörde web admin panelini Ubuntu sunucuda systemd servisi olarak çalıştırmak için gerekli dosyalar bulunmaktadır.

## 📋 Dosyalar

- **cotabot-panel.service** - Systemd servis tanımı
- **install_panel_service.sh** - Servis kurulum script'i
- **uninstall_panel_service.sh** - Servis kaldırma script'i

## 🚀 Kurulum

### 1. Ubuntu sunucuya SSH ile bağlanın

```bash
ssh kullanici@sunucu_ip
```

### 2. Cotabot dizinine gidin

```bash
cd /path/to/cotabot/COTABOT\ -\ DEV
```

### 3. Kurulum script'ini çalıştırın

```bash
chmod +x install_panel_service.sh
sudo ./install_panel_service.sh
```

Script otomatik olarak:
- Servis dosyasını systemd dizinine kopyalar
- Servisi otomatik başlatma için etkinleştirir
- Servisi başlatır

## 🔧 Servis Yönetimi

### Durum Kontrolü
```bash
sudo systemctl status cotabot-panel
```

### Servisi Başlat
```bash
sudo systemctl start cotabot-panel
```

### Servisi Durdur
```bash
sudo systemctl stop cotabot-panel
```

### Servisi Yeniden Başlat
```bash
sudo systemctl restart cotabot-panel
```

### Log'ları Görüntüle
```bash
# Canlı log takibi
sudo journalctl -u cotabot-panel -f

# Son 100 satırı göster
sudo journalctl -u cotabot-panel -n 100
```

### Otomatik Başlatmayı Devre Dışı Bırak
```bash
sudo systemctl disable cotabot-panel
```

### Otomatik Başlatmayı Etkinleştir
```bash
sudo systemctl enable cotabot-panel
```

## 🌐 Panel Erişimi

Panel çalıştıktan sonra şu adreslerden erişilebilir:

- **Sunucuda:** http://localhost:5000
- **Ağdan:** http://SUNUCU_IP:5000

## 🗑️ Servisi Kaldırma

```bash
sudo ./uninstall_panel_service.sh
```

## ⚙️ Yapılandırma

### Servis Dosyası Düzenleme

Eğer port, environment değişkenleri veya diğer ayarları değiştirmek isterseniz:

1. Servis dosyasını düzenleyin:
```bash
sudo nano /etc/systemd/system/cotabot-panel.service
```

2. Systemd'yi yeniden yükleyin:
```bash
sudo systemctl daemon-reload
```

3. Servisi yeniden başlatın:
```bash
sudo systemctl restart cotabot-panel
```

## 🔒 Güvenlik Notları

- Production ortamında mutlaka güçlü bir API key kullanın
- Firewall kurallarını yapılandırın (ufw veya iptables)
- Nginx reverse proxy kullanmayı düşünün
- HTTPS için SSL sertifikası ekleyin

## 🐛 Sorun Giderme

### Servis başlamıyor

1. Log'ları kontrol edin:
```bash
sudo journalctl -u cotabot-panel -xe
```

2. Python ve bağımlılıkların kurulu olduğundan emin olun:
```bash
pip3 install -r web_admin/requirements_web.txt
```

3. Çalışma dizininin ve dosya izinlerinin doğru olduğunu kontrol edin

### Port 5000 kullanımda

Başka bir servis port 5000'i kullanıyorsa:

1. Servis dosyasındaki `api.py` ayarlarını değiştirin
2. Veya `config.py` dosyasında PORT değişkenini güncelleyin

### Veritabanı erişim hatası

1. Database path'in doğru olduğunu kontrol edin
2. Dosya izinlerini kontrol edin:
```bash
ls -la cotabot_dev.db
```
