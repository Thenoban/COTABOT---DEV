# Python 3.9'un hafif bir sürümünü kullanıyoruz
FROM python:3.9-slim

# Çalışma dizinini ayarlıyoruz
WORKDIR /app

# Sistem bağımlılıklarını yüklüyoruz (PyNaCl ve diğerleri için)
RUN apt-get update && apt-get install -y \
    gcc \
    libsodium-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Gerekli dosyaları kopyalıyoruz
COPY requirements.txt .

# Bağımlılıkları yüklüyoruz
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodlarını kopyalıyoruz
COPY . .

# Botu çalıştırıyoruz
CMD ["python", "main.py"]
