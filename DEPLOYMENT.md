# 🐳 Cotabot Web Panel - Docker Deployment Guide

**Son Güncelleme:** 17 Ocak 2026  
**Deployment Yöntemi:** Docker Container

---

## 📋 Gereksinimler

- Docker (20.10+)
- Docker Compose (1.29+)
- Minimum 512MB RAM
- Port 5000 erişimi

---

## 🚀 Hızlı Başlangıç

### 1. Docker Image Build

```bash
cd "\\192.168.1.174\cotabot\COTABOT - DEV"

# Image oluştur
docker build -f web_panel.Dockerfile -t cotabot-panel:latest .
```

### 2. Container Başlat

```bash
# Docker Compose ile başlat
docker-compose -f docker-compose-panel.yml up -d

# Log'ları izle
docker-compose -f docker-compose-panel.yml logs -f cotabot-panel
```

### 3. Erişim

- **Web Arayüzü:** http://localhost:5000
- **Network Erişimi:** http://[SUNUCU_IP]:5000
- **API Key:** `cotabot-admin-2024` (değiştirin!)

---

## 📁 Dosya Yapısı

```
COTABOT - DEV/
├── web_panel.Dockerfile          # Web panel Docker image
├── docker-compose-panel.yml      # Docker Compose config
├── web_admin/
│   ├── api.py                   # Flask application
│   ├── gunicorn_config.py       # Gunicorn WSGI config
│   └── requirements_web.txt     # Python dependencies
├── database/                    # Database models & adapter
├── cotabot_dev.db              # SQLite database (mounted)
└── .env                        # Environment variables
```

---

## 🔧 Docker Komutları

### Container Yönetimi

```bash
# Durumu kontrol et
docker ps | grep cotabot-panel

# Detaylı durum
docker-compose -f docker-compose-panel.yml ps

# Başlat
docker-compose -f docker-compose-panel.yml start

# Durdur
docker-compose -f docker-compose-panel.yml stop

# Yeniden başlat
docker-compose -f docker-compose-panel.yml restart

# Kaldır (container + network)
docker-compose -f docker-compose-panel.yml down

# Kaldır (+ volumes)
docker-compose -f docker-compose-panel.yml down -v
```

### Log Yönetimi

```bash
# Canlı log izle
docker-compose -f docker-compose-panel.yml logs -f

# Son 100 satır
docker-compose -f docker-compose-panel.yml logs --tail=100

# Belirli zamandan itibaren
docker-compose -f docker-compose-panel.yml logs --since 2h
```

### Container İçine Giriş

```bash
# Bash shell aç
docker exec -it cotabot-web-panel bash

# Python REPL
docker exec -it cotabot-web-panel python

# Tek komut çalıştır
docker exec cotabot-web-panel python check_db.py
```

---

## ⚙️ Konfigürasyon

### Environment Variables

`.env` dosyasında ayarlanmalı:

```env
# Web Admin API Key (ÖNEMLİ: Değiştirin!)
WEB_ADMIN_API_KEY=your-secure-api-key-here

# Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token

# BattleMetrics API
BATTLEMETRICS_TOKEN=your_battlemetrics_token

# Google Sheets (opsiyonel)
GOOGLE_SHEET_KEY=your_sheet_key
```

### Port Değiştirme

`docker-compose-panel.yml` dosyasında:

```yaml
ports:
  - "8080:5000"  # Host:Container
```

### Database Path

Varsayılan: `./cotabot_dev.db`

Değiştirmek için `docker-compose-panel.yml`:

```yaml
volumes:
  - /path/to/your/database.db:/app/cotabot_dev.db
```

---

## 🧪 Test ve Verification

### 1. Health Check

```bash
# Container health durumu
docker inspect cotabot-web-panel | grep -A 10 Health

# Manuel health check
curl http://localhost:5000/
```

### 2. API Test

```bash
# Players endpoint
curl -X GET "http://localhost:5000/api/players" \
  -H "X-API-Key: cotabot-admin-2024"

# Events endpoint
curl -X GET "http://localhost:5000/api/events" \
  -H "X-API-Key: cotabot-admin-2024"

# Dashboard stats
curl -X GET "http://localhost:5000/api/stats/dashboard" \
  -H "X-API-Key: cotabot-admin-2024"
```

### 3. Database Bağlantısı

```bash
# Database kontrol
docker exec cotabot-web-panel python -c "
from database.adapter import DatabaseAdapter
db = DatabaseAdapter('cotabot_dev.db')
print('✅ Database bağlantısı başarılı')
"
```

### 4. Auto-Restart Test

```bash
# Container'ı durdur
docker stop cotabot-web-panel

# 5 saniye bekle
sleep 5

# Durum kontrol et (otomatik başlamalı)
docker ps | grep cotabot-panel
```

---

##🔒 Güvenlik

### API Key Değiştirme

> [!WARNING]
> Production'da varsayılan API key'i MUTLAKA değiştirin!

1. `.env` dosyasını düzenle:
```env
WEB_ADMIN_API_KEY=super-gizli-anahtar-12345
```

2. `config.py` dosyasında da ayarlayın (fallback)

3. Container'ı yeniden başlatın:
```bash
docker-compose -f docker-compose-panel.yml restart
```

### Firewall Kuralları

```bash
# Sadece local network'e izin ver
sudo ufw allow from 192.168.1.0/24 to any port 5000

# Belirli IP'ye izin ver
sudo ufw allow from 192.168.1.100 to any port 5000
```

---

## 📊 Monitoring

### Resource Kullanımı

```bash
# Real-time stats
docker stats cotabot-web-panel

# CPU ve Memory limitleri (.yml dosyasında)
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

### Log Rotation

Docker log rotation ayarı:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 🐛 Troubleshooting

### Container başlamıyor

```bash
# Detaylı hata log'u
docker-compose -f docker-compose-panel.yml logs

# Image'i yeniden build et
docker-compose -f docker-compose-panel.yml build --no-cache
docker-compose -f docker-compose-panel.yml up -d
```

### Port çakışması

```bash
# Port 5000'i kullanan process'i bul
netstat -tulpn | grep 5000

# Veya lsof (Linux)
lsof -i :5000

# Farklı port kullan (docker-compose-panel.yml)
ports:
  - "5001:5000"
```

### Database erişim hatası

```bash
# Permission kontrolü
ls -la cotabot_dev.db

# Database path kontrolü
docker exec cotabot-web-panel ls -la /app/cotabot_dev.db

# Volume mount kontrolü
docker inspect cotabot-web-panel | grep -A 10 Mounts
```

### Gunicorn hatası

```bash
# Gunicorn config test
docker exec cotabot-web-panel python -c "
import web_admin.gunicorn_config
print('✅ Config OK')
"

# Manuel Flask başlat (debug)
docker exec cotabot-web-panel python web_admin/api.py
```

---

## 🔄 Production Best Practices

### 1. Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name panel.cotabot.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. SSL Certificate (Let's Encrypt)

```bash
sudo certbot --nginx -d panel.cotabot.com
```

### 3. Database Backup

```bash
# Otomatik günlük backup (crontab)
0 2 * * * docker exec cotabot-web-panel cp /app/cotabot_dev.db /app/backups/cotabot_$(date +\%Y\%m\%d).db
```

### 4. Container Updates

```bash
# Yeni image build
docker build -f web_panel.Dockerfile -t cotabot-panel:latest .

# Güvenli update (zero downtime)
docker-compose -f docker-compose-panel.yml up -d --no-deps --build cotabot-panel
```

---

## 📖 Ek Kaynaklar

- [Docker Documentation](https://docs.docker.com/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Flask Production Guide](https://flask.palletsprojects.com/en/latest/deploying/)

---

## 🆘 Destek

Problem yaşarsanız:

1. Container log'larını kontrol edin
2. Health check yapın
3. Database bağlantısını test edin
4. Issue açın veya destek isteyin

---

**Deployment başarıyla tamamlandı! 🎉**
