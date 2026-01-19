# Cotabot Web Admin Panel

Modern web tabanlı admin panel for Cotabot Discord botu.

## 📋 Özellikler

- 📊 **Dashboard**: Genel istatistikler ve aktivite grafikleri
- 👥 **Player Management**: Oyuncu ekleme, düzenleme, silme ve arama
- 📅 **Events**: Etkinlik yönetimi ve katılımcı takibi
- 📈 **Reports**: Hall of Fame ve performans raporları
- 🖥️ **Server Status**: Canlı sunucu durumu izleme
- ⚙️ **Settings**: Ayarlar ve yapılandırma

## 🚀 Kurulum

### Gereksinimler

- Python 3.8+
- Flask ve bağımlılıkları

### Adımlar

1. **Bağımlılıkları yükleyin**:
```bash
cd "\\192.168.1.174\cotabot\COTABOT - DEV\web_admin"
pip install -r requirements_web.txt
```

2. **API'yi başlatın**:
```bash
python api.py
```

3. **Tarayıcıda açın**:
```
http://localhost:5000
```

veya network üzerinden:
```
http://192.168.1.174:5000
```

## 🔐 Giriş

Varsayılan API Key: `cotabot-admin-2024`

> ⚠️ **Güvenlik**: Production ortamında mutlaka `config.py` dosyasında `API_KEY` değerini değiştirin veya `.env` dosyasında `WEB_ADMIN_API_KEY` ayarlayın.

## 📁 Proje Yapısı

```
web_admin/
├── api.py                 # Flask REST API
├── config.py              # Yapılandırma
├── auth.py                # Authentication
├── requirements_web.txt   # Python bağımlılıkları
└── static/
    ├── index.html         # Ana HTML
    ├── css/
    │   └── styles.css     # Modern dark theme CSS
    └── js/
        ├── app.js         # Ana uygulama
        ├── utils/
        │   ├── api-client.js      # API istekleri
        │   └── chart-config.js    # Chart.js yapılandırması
        └── pages/
            ├── dashboard.js       # Dashboard sayfası
            ├── players.js         # Oyuncu yönetimi
            ├── events.js          # Etkinlikler
            ├── reports.js         # Raporlar
            ├── server.js          # Sunucu durumu
            └── settings.js        # Ayarlar
```

## 🎨 Tasarım

- **Dark Mode**: Modern koyu tema
- **Glassmorphism**: Saydam blur efektleri
- **Smooth Animations**: Akıcı geçişler ve hover efektleri
- **Responsive**: Mobil, tablet ve desktop uyumlu
- **Premium**: Gradient renkler ve modern tipografi

## 🔌 API Endpoints

### Dashboard
- `GET /api/stats/dashboard` - Genel istatistikler
- `GET /api/stats/activity-chart` - Aktivite grafiği

### Players
- `GET /api/players` - Oyuncu listesi
- `GET /api/players/<steam_id>` - Oyuncu detayı
- `POST /api/players` - Oyuncu ekle
- `PUT /api/players/<steam_id>` - Oyuncu güncelle
- `DELETE /api/players/<steam_id>` - Oyuncu sil

### Events
- `GET /api/events` - Tüm etkinlikler
- `GET /api/events/active` - Aktif etkinlikler

### Reports
- `GET /api/reports/hall-of-fame` - Hall of Fame kayıtları

### Server
- `GET /api/server/status` - Sunucu durumu

## ⚙️ Yapılandırma

`config.py` dosyasını düzenleyerek ayarları değiştirebilirsiniz:

```python
# API Configuration
HOST = "0.0.0.0"  # Tüm network arayüzlerinde dinle
PORT = 5000       # Port numarası

# Security
API_KEY = "cotabot-admin-2024"  # API anahtarı (değiştirin!)

# Database
DATABASE_PATH = "../cotabot_dev.db"  # Bot veritabanı
```

## 🔄 Bot ile Etkileşim

Web panel, Discord bot ile aynı veritabanını (`cotabot_dev.db`) kullanır. Her iki sistem de eşzamanlı çalışabilir:

- Web panelden eklenen oyuncular bot komutlarında görünür
- Bot ile eklenen oyuncular web panelde görünür
- Tüm istatistikler gerçek zamanlı güncellenir

## 🛠️ Troubleshooting

### Port zaten kullanımda
Farklı bir port kullanmak için `config.py`'de `PORT` değerini değiştirin.

### Veritabanı bulunamadı
`config.py`'de `DATABASE_PATH` yolunun doğru olduğundan emin olun.

### CORS hataları
`config.py`'de `CORS_ORIGINS` ayarını kontrol edin.

## 📝 Notlar

- Web panel read-write erişime sahiptir, dikkatli kullanın
- Production ortamında HTTPS kullanımı önerilir
- Düzenli veritabanı yedeklemeleri alın

## 🎯 Gelecek Özellikler

- [ ] Gelişmiş filtreleme ve sıralama
- [ ] Toplu işlemler
- [ ] Export/Import fonksiyonları
- [ ] Real-time WebSocket güncellemeleri
- [ ] Kullanıcı rolleri ve izinleri

---

Made with ❤️ for Squad community
