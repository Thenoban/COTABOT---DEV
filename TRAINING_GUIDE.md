# Training Match Tracker - Kullanım Kılavuzu

## Komutlar

### 1. Maç Başlatma
```
!training_start [harita_adı]
```
Yeni bir training maçı başlatır.

**Örnek:**
```
!training_start Gorodok
!training_start Mutaha
```

### 2. Maç Bitirme
```
!training_end
```
Aktif maçı sonlandırır.

### 3. Manuel KDA Ekleme
```
!training_kda_add <oyuncu_ismi> <kills> <deaths> [assists]
```
Fotoğraftan okuduğunuz KDA verilerini ekler.

**Örnek:**
```
!training_kda_add "Player1" 15 8 3
!training_kda_add Player2 20 12 5
```

**Toplu Ekleme İçin:**
Her oyuncu için komutu tekrarlayın:
```
!training_kda_add Player1 15 8 3
!training_kda_add Player2 20 12 5
!training_kda_add Player3 18 10 4
```

### 4. Maç Raporu
```
!training_report [match_id]
```
Maç raporunu gösterir. Match ID belirtilmezse son maçı gösterir.

**Örnek:**
```
!training_report
!training_report 1
```

### 5. Maç Listesi
```
!training_list
```
Tüm maçları listeler.

## Workflow Örneği

### Maç 1:
```
1. !training_start Gorodok
2. [Maç oynanır...]
3. !training_end
4. [Oyun içi skorboard fotoğrafını çekin]
5. !training_kda_add Player1 15 8 3
6. !training_kda_add Player2 20 12 5
7. ... (diğer oyuncular)
8. !training_report
```

### Maç 2:
```
1. !training_start Mutaha
2. [Maç oynanır...]
3. !training_end
4. [Skorboard fotoğrafı]
5. !training_kda_add Player1 18 10 4
6. ... (diğer oyuncular)
7. !training_report
```

### Raporları Görüntüleme:
```
!training_list           # Tüm maçları listele
!training_report 1       # İlk maçın raporu
!training_report 2       # İkinci maçın raporu
```

## Notlar

- Komutları kullanabilmek için admin yetkisi gereklidir
- Aynı anda sadece 1 aktif maç olabilir
- Manuel KDA ekleme sınırsızdır, istediğiniz kadar oyuncu ekleyebilirsiniz
- Raporda oyuncular K/D oranına göre sıralanır
- Veri kaynağı göstergeleri:
  - 📊 Delta (Otomatik BattleMetrics)
  - 📸 Manuel (Elle girilen)
  - 🔀 Hibrit (Her ikisi)
