# Training Match Tracker - Hızlı Referans

## Yeni Komut Eklendi! ✨

### Belirli Match ID'ye KDA Ekleme
```
!1training_kda_add_to <match_id> <oyuncu_ismi> <kills> <deaths> [assists]
```

**Örnek - Maç #3'e veri ekle:**
```
!1training_kda_add_to 3 "Player1" 25 10 5
!1training_kda_add_to 3 "Player2" 18 12 3
!1training_kda_add_to 3 "Player3" 30 8 7
```

## Tüm Komutlar

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `!1training_start [harita]` | Yeni maç başlat | `!1training_start Gorodok` |
| `!1training_end` | Aktif maçı bitir | `!1training_end` |
| `!1training_players [id]` | **Katılımcıları listele** | `!1training_players 4` |
| `!1training_kda_add <isim> <k> <d> [a]` | **Son maça** KDA ekle | `!1training_kda_add Player1 15 8 3` |
| `!1training_kda_add_to <id> <isim> <k> <d> [a]` | **Belirli maça** KDA ekle | `!1training_kda_add_to 3 Player1 15 8 3` |
| `!1training_report [id]` | Maç raporu | `!1training_report 3` |
| `!1training_list` | Tüm maçları listele | `!1training_list` |

## İkinci Maç İçin Delta Testi

**Şimdi yapılacaklar:**

1. **İkinci maçı başlat:**
   ```
   !1training_start Match2_Harita
   ```

2. **Maç boyunca:**
   - Bot otomatik olarak başlangıç snapshot'ı aldı ✅
   - Oyuncular training sunucusunda oynuyor
   - BattleMetrics canlı veri topluyor

3. **Maç bittiğinde:**
   ```
   !1training_end
   ```
   - Bot bitiş snapshot'ı alacak 📸
   - Delta otomatik hesaplanacak 🔢
   - Raporda delta verileri görünecek 📊

4. **Raporu kontrol et:**
   ```
   !1training_report
   ```
   - 📊 simgesi = Delta (otomatik hesaplanan)
   - 📸 simgesi = Manuel eklenen
   - 🔀 simgesi = Her ikisi (hibrit)

## İlk Maç (#3) İçin Manuel Ekleme

```
!1training_kda_add_to 3 "Oyuncu1" kills deaths assists
!1training_kda_add_to 3 "Oyuncu2" kills deaths assists
...
```

**Not:** Bot yeniden başlatıldı mı? Değişiklikler yüklensin!
