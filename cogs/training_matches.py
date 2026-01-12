import discord
from discord.ext import commands
import aiohttp
import os
import json
import asyncio
import datetime
from typing import Optional, Dict, List
import logging

from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, BM_API_URL, BM_API_KEY, COLORS

logger = logging.getLogger("TrainingMatches")


class TrainingMatches(commands.Cog):
    """Training maçlarını takip eden cog - Delta hesaplama ve manuel KDA girişi"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.training_db_file = "training_db.json"
        self.training_server_ip = "84.200.135.219:7789"
        self.active_match = None  # Currently active match ID
        
    async def cog_load(self):
        """Cog yüklendiğinde HTTP session oluştur"""
        self.session = aiohttp.ClientSession()
        logger.info("TrainingMatches cog loaded")
        
    async def cog_unload(self):
        """Cog kaldırıldığında session'ı kapat"""
        if self.session:
            await self.session.close()
        logger.info("TrainingMatches cog unloaded")
    
    def get_headers(self):
        """BattleMetrics API headers"""
        if BM_API_KEY:
            return {"Authorization": f"Bearer {BM_API_KEY}"}
        return {}
    
    async def check_permissions(self, ctx):
        """Admin yetkisi kontrolü"""
        if ctx.author.guild_permissions.administrator:
            return True
        if ctx.author.id in ADMIN_USER_IDS:
            return True
        for role in ctx.author.roles:
            if role.id in ADMIN_ROLE_IDS:
                return True
        await ctx.send("❌ Bu komutu kullanmak için yetkiniz yok.")
        return False
    
    def load_training_db(self) -> dict:
        """Training database'i yükle"""
        if not os.path.exists(self.training_db_file):
            return {"matches": [], "config": {"next_match_id": 1}}
        
        try:
            with open(self.training_db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading training DB: {e}")
            return {"matches": [], "config": {"next_match_id": 1}}
    
    def save_training_db(self, data: dict):
        """Training database'i kaydet"""
        try:
            with open(self.training_db_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving training DB: {e}")
    
    async def fetch_battlemetrics_snapshot(self, server_id: str) -> Optional[Dict]:
        """
        BattleMetrics API'den oyuncu snapshot'ı al
        
        Returns:
            Dict with player stats or None if error
        """
        try:
            # API'den sunucu ve oyuncu bilgilerini çek
            url = f"{BM_API_URL}/servers/{server_id}?include=player,identifier"
            
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status != 200:
                    logger.error(f"BattleMetrics API error: {response.status}")
                    return None
                
                data = await response.json()
                
                # Snapshot formatı
                snapshot = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "server_id": server_id,
                    "players": []
                }
                
                # Aktif oyuncuları kaydet
                included = data.get('included', [])
                
                # Player ID -> Steam ID mapping
                player_steam_map = {}
                for item in included:
                    if item.get('type') == 'identifier':
                        attrs = item.get('attributes', {})
                        if attrs.get('type') == 'steamID':
                            steam_id = attrs.get('identifier')
                            rels = item.get('relationships', {})
                            player_data = rels.get('player', {}).get('data')
                            if player_data and player_data.get('id'):
                                player_steam_map[player_data['id']] = steam_id
                
                # Player bilgilerini topla
                for item in included:
                    if item.get('type') == 'player':
                        player_id = item.get('id')
                        attrs = item.get('attributes', {})
                        
                        player_name = attrs.get('name', 'Unknown')
                        steam_id = player_steam_map.get(player_id, 'unknown')
                        
                        snapshot['players'].append({
                            'steam_id': steam_id,
                            'name': player_name,
                            'battlemetrics_id': player_id
                        })
                
                logger.info(f"Snapshot captured: {len(snapshot['players'])} players")
                return snapshot
                
        except Exception as e:
            logger.error(f"Error fetching BattleMetrics snapshot: {e}")
            return None
    
    async def fetch_player_stats(self, steam_id: str) -> Optional[Dict]:
        """
        squad_db.json'dan oyuncu istatistiklerini al
        
        Returns:
            Player stats dict or None
        """
        try:
            if not os.path.exists("squad_db.json"):
                return None
            
            with open("squad_db.json", "r", encoding="utf-8") as f:
                db = json.load(f)
            
            for player in db.get("players", []):
                if player.get("steam_id") == steam_id:
                    return {
                        'steam_id': steam_id,
                        'name': player.get('name', 'Unknown'),
                        'stats': player.get('stats', {}),
                        'season_stats': player.get('season_stats', {})
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching player stats for {steam_id}: {e}")
            return None
    
    async def find_steam_id_by_name(self, player_name: str) -> Optional[str]:
        """
        squad_db.json'dan oyuncu ismine göre Steam ID bulur
        
        Args:
            player_name: Oyuncu ismi (case-insensitive)
            
        Returns:
            Steam ID string or None
        """
        try:
            if not os.path.exists("squad_db.json"):
                return None
            
            with open("squad_db.json", "r", encoding="utf-8") as f:
                db = json.load(f)
            
            # Case-insensitive arama
            player_name_lower = player_name.lower().strip()
            
            for player in db.get("players", []):
                if player.get("name", "").lower().strip() == player_name_lower:
                    steam_id = player.get("steam_id")
                    if steam_id:
                        logger.info(f"Found Steam ID {steam_id} for player {player_name}")
                        return steam_id
            
            logger.debug(f"No Steam ID found for player {player_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding Steam ID for {player_name}: {e}")
            return None
    
    async def calculate_delta(self, match: dict) -> bool:
        """
        Maç başı ve sonu snapshot'larını karşılaştırarak delta hesaplar
        
        NOT: squad_db.json'daki stats'lar maç sırasında değişmez, sadece maç sonunda sync edilir.
        Bu yüzden delta hesaplaması için snapshot'lardaki oyuncu listesini kullanıp,
        manuel veri girişi yapılmasını bekleriz VEYA maç sonunda !squad_sync çalıştırılır.
        
        Args:
            match: Match dictionary with snapshot_start and snapshot_end
            
        Returns:
            True if delta calculated successfully
        """
        try:
            snapshot_start = match.get('snapshot_start')
            snapshot_end = match.get('snapshot_end')
            
            if not snapshot_start or not snapshot_end:
                logger.warning("Missing snapshots for delta calculation")
                return False
            
            # Steam ID -> başlangıç snapshot mapping
            start_players = {p['steam_id']: p for p in snapshot_start.get('players', [])}
            end_players_set = {p['steam_id'] for p in snapshot_end.get('players', [])}
            
            # Tüm maç boyunca oynayan oyuncuları bul (hem başta hem sonda olan)
            players_to_add = []
            
            for end_player in snapshot_end.get('players', []):
                steam_id = end_player['steam_id']
                player_name = end_player['name']
                
                # Başlangıçta yoksa skip (sadece maç sonuna katılanlar)
                if steam_id not in start_players:
                    logger.debug(f"Player {player_name} joined mid-match, skipping delta")
                    continue
                
                # Placeholder delta: Snapshot'tan istatistik alamadığımız için
                # delta hesaplanamıyor, manuel veri bekleniyor
                players_to_add.append({
                    'steam_id': steam_id,
                    'name': player_name,
                    'kills_delta': None,  # squad_db stats güncel olmadığı için hesaplanamıyor
                    'deaths_delta': None,
                    'kills_manual': None,
                    'deaths_manual': None,
                    'assists_manual': None,
                    'final_kills': 0,  # Manuel giriş bekliyor
                    'final_deaths': 0,
                    'final_assists': 0,
                    'kd_ratio': 0.0,
                    'data_source': 'pending'  # Manuel veri bekleniyor
                })
            
            # Match'e oyuncuları ekle
            match['players'] = players_to_add
            
            logger.info(f"Delta placeholder created for {len(players_to_add)} players (manual KDA entry needed)")
            return True
            
        except Exception as e:
            logger.error(f"Error calculating delta: {e}", exc_info=True)
            return False
    
    @commands.command(name='training_start', aliases=['ts'])
    async def training_start(self, ctx, *, map_name: str = "Unknown"):
        """
        Yeni bir training maçı başlatır ve snapshot alır
        
        Kullanım: !training_start [harita_adı]
        Örnek: !training_start Gorodok
        """
        if not await self.check_permissions(ctx):
            return
        
        # Aktif maç kontrolü
        if self.active_match:
            await ctx.send("❌ Zaten aktif bir maç var! Önce `!training_end` ile bitirin.")
            return
        
        await ctx.send("🎮 **Training maçı başlatılıyor...**")
        
        # BattleMetrics'den snapshot al (training server ID'si gerekli)
        # Şimdilik manuel olarak server ID belirleyelim
        # Kullanıcı kendi server ID'sini config'e ekleyebilir
        
        db = self.load_training_db()
        
        # Yeni match ID
        match_id = str(db['config']['next_match_id'])
        db['config']['next_match_id'] += 1
        
        # Match oluştur
        new_match = {
            'match_id': match_id,
            'server_ip': self.training_server_ip,
            'map': map_name,
            'start_time': datetime.datetime.now().isoformat(),
            'end_time': None,
            'status': 'active',
            'snapshot_start': None,
            'snapshot_end': None,
            'players': []
        }
        
        # Snapshot al (eğer server ID varsa)
        from .utils.config import TRAINING_SERVER_ID
        if TRAINING_SERVER_ID:
            snapshot = await self.fetch_battlemetrics_snapshot(TRAINING_SERVER_ID)
            if snapshot:
                new_match['snapshot_start'] = snapshot
                logger.info(f"Match {match_id} started with snapshot: {len(snapshot.get('players', []))} players")
        
        db['matches'].append(new_match)
        self.save_training_db(db)
        
        # Aktif match'i set et
        self.active_match = match_id
        
        embed = discord.Embed(
            title="🎮 Training Maçı Başladı!",
            description=f"**Maç ID:** `{match_id}`\n**Harita:** {map_name}\n**Başlangıç:** {datetime.datetime.now().strftime('%H:%M:%S')}",
            color=discord.Color(COLORS.SUCCESS)
        )
        
        embed.add_field(
            name="📊 Veri Toplama",
            value="Maç bittiğinde `!training_end` komutu ile sonlandırın.",
            inline=False
        )
        
        embed.add_field(
            name="📸 Manuel KDA",
            value="Maç sonrası ekran görüntüsünden veri eklemek için `!training_kda_add` kullanın.",
            inline=False
        )
        
        embed.set_footer(text=f"Server: {self.training_server_ip}")
        
        await ctx.send(embed=embed)
        logger.info(f"Training match {match_id} started by {ctx.author}")
    
    @commands.command(name='training_end', aliases=['te'])
    async def training_end(self, ctx):
        """
        Aktif training maçını sonlandırır ve delta hesaplar
        
        Kullanım: !training_end
        """
        if not await self.check_permissions(ctx):
            return
        
        if not self.active_match:
            await ctx.send("❌ Aktif bir maç yok! `!training_start` ile maç başlatın.")
            return
        
        await ctx.send("⏱️ **Training maçı sonlandırılıyor...**")
        
        db = self.load_training_db()
        
        # Aktif match'i bul
        match = None
        for m in db['matches']:
            if m['match_id'] == self.active_match:
                match = m
                break
        
        if not match:
            await ctx.send("❌ Aktif maç veritabanında bulunamadı!")
            self.active_match = None
            return
        
        # Maçı kapat
        match['end_time'] = datetime.datetime.now().isoformat()
        match['status'] = 'completed'
        
        # Snapshot al ve delta hesapla
        from .utils.config import TRAINING_SERVER_ID
        if TRAINING_SERVER_ID:
            snapshot_end = await self.fetch_battlemetrics_snapshot(TRAINING_SERVER_ID)
            if snapshot_end:
                match['snapshot_end'] = snapshot_end
                logger.info(f"Match {match['match_id']} ended with snapshot: {len(snapshot_end.get('players', []))} players")
                
                # Delta hesaplama
                if match.get('snapshot_start'):
                    delta_calculated = await self.calculate_delta(match)
                    if delta_calculated:
                        logger.info(f"Delta calculated for {len(match['players'])} players")
        
        self.save_training_db(db)
        self.active_match = None
        
        # Süreyi hesapla
        start_time = datetime.datetime.fromisoformat(match['start_time'])
        end_time = datetime.datetime.fromisoformat(match['end_time'])
        duration = end_time - start_time
        duration_mins = int(duration.total_seconds() / 60)
        
        embed = discord.Embed(
            title="🏁 Training Maçı Bitti!",
            description=f"**Maç ID:** `{match['match_id']}`\n**Harita:** {match['map']}\n**Süre:** {duration_mins} dakika",
            color=discord.Color(COLORS.GOLD)
        )
        
        embed.add_field(
            name="📊 Sonraki Adımlar",
            value="• Ekran görüntüsünden KDA eklemek için: `!training_kda_add`\n• Rapor görmek için: `!training_report " + match['match_id'] + "`",
            inline=False
        )
        
        await ctx.send(embed=embed)
        logger.info(f"Training match {match['match_id']} ended by {ctx.author}")
    
    @commands.command(name='training_kda_add', aliases=['tka'])
    async def training_kda_add(self, ctx, player_name: str, kills: int, deaths: int, assists: int = 0):
        """
        Manuel KDA verisi ekler (fotoğraftan)
        
        Kullanım: !training_kda_add <oyuncu_ismi> <kills> <deaths> [assists]
        Örnek: !training_kda_add "Player1" 15 8 3
        """
        if not await self.check_permissions(ctx):
            return
        
        # Son tamamlanan maçı bul
        db = self.load_training_db()
        
        if not db['matches']:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        # Son maçı al
        last_match = db['matches'][-1]
        
        # Oyuncu isminden Steam ID bul
        steam_id = await self.find_steam_id_by_name(player_name)
        if not steam_id:
            steam_id = 'unknown'
            logger.info(f"Steam ID not found for {player_name}, using 'unknown'")
        
        # Oyuncuyu bul veya ekle
        player_found = False
        for player in last_match['players']:
            if player['name'].lower() == player_name.lower():
                # Güncelle
                player['kills_manual'] = kills
                player['deaths_manual'] = deaths
                player['assists_manual'] = assists
                player['final_kills'] = kills
                player['final_deaths'] = deaths
                player['final_assists'] = assists
                player['kd_ratio'] = round(kills / deaths, 2) if deaths > 0 else kills
                player['data_source'] = 'manual'
                player_found = True
                break
        
        if not player_found:
            # Yeni oyuncu ekle
            last_match['players'].append({
                'name': player_name,
                'steam_id': steam_id,  # Auto-found or 'unknown'
                'kills_delta': None,
                'deaths_delta': None,
                'kills_manual': kills,
                'deaths_manual': deaths,
                'assists_manual': assists,
                'final_kills': kills,
                'final_deaths': deaths,
                'final_assists': assists,
                'kd_ratio': round(kills / deaths, 2) if deaths > 0 else kills,
                'data_source': 'manual'
            })
        
        self.save_training_db(db)
        
        embed = discord.Embed(
            title="✅ KDA Eklendi",
            description=f"**Oyuncu:** {player_name}\n**Maç:** `{last_match['match_id']}`",
            color=discord.Color(COLORS.SUCCESS)
        )
        
        embed.add_field(name="⚔️ Kills", value=str(kills), inline=True)
        embed.add_field(name="💀 Deaths", value=str(deaths), inline=True)
        embed.add_field(name="🤝 Assists", value=str(assists), inline=True)
        embed.add_field(name="📊 K/D", value=f"{round(kills/deaths, 2) if deaths > 0 else kills}", inline=True)
        
        await ctx.send(embed=embed)
        logger.info(f"Manual KDA added for {player_name} by {ctx.author}")
    
    @commands.command(name='training_kda_add_to', aliases=['tkat'])
    async def training_kda_add_to(self, ctx, match_id: str, player_name: str, kills: int, deaths: int, assists: int = 0):
        """
        Belirli bir maça manuel KDA verisi ekler
        
        Kullanım: !training_kda_add_to <match_id> <oyuncu_ismi> <kills> <deaths> [assists]
        Örnek: !training_kda_add_to 3 "Player1" 15 8 3
        """
        if not await self.check_permissions(ctx):
            return
        
        # Belirtilen maçı bul
        db = self.load_training_db()
        
        if not db['matches']:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        # Match ID'yi bul
        target_match = None
        for match in db['matches']:
            if match['match_id'] == match_id:
                target_match = match
                break
        
        if not target_match:
            await ctx.send(f"❌ Maç ID `{match_id}` bulunamadı! Mevcut maçları görmek için `!training_list` kullanın.")
            return
        
        # Oyuncu isminden Steam ID bul
        steam_id = await self.find_steam_id_by_name(player_name)
        if not steam_id:
            steam_id = 'unknown'
            logger.info(f"Steam ID not found for {player_name}, using 'unknown'")
        
        # Oyuncuyu bul veya ekle
        player_found = False
        for player in target_match['players']:
            if player['name'].lower() == player_name.lower():
                # Güncelle
                player['kills_manual'] = kills
                player['deaths_manual'] = deaths
                player['assists_manual'] = assists
                
                # Delta varsa hibrit, yoksa manuel
                if player.get('kills_delta') is not None:
                    player['final_kills'] = kills
                    player['final_deaths'] = deaths
                    player['final_assists'] = assists
                    player['data_source'] = 'hybrid'
                else:
                    player['final_kills'] = kills
                    player['final_deaths'] = deaths
                    player['final_assists'] = assists
                    player['data_source'] = 'manual'
                
                player['kd_ratio'] = round(kills / deaths, 2) if deaths > 0 else kills
                player_found = True
                break
        
        if not player_found:
            # Yeni oyuncu ekle
            target_match['players'].append({
                'name': player_name,
                'steam_id': steam_id,  # Auto-found or 'unknown'
                'kills_delta': None,
                'deaths_delta': None,
                'kills_manual': kills,
                'deaths_manual': deaths,
                'assists_manual': assists,
                'final_kills': kills,
                'final_deaths': deaths,
                'final_assists': assists,
                'kd_ratio': round(kills / deaths, 2) if deaths > 0 else kills,
                'data_source': 'manual'
            })
        
        self.save_training_db(db)
        
        embed = discord.Embed(
            title="✅ KDA Eklendi (Belirli Maç)",
            description=f"**Oyuncu:** {player_name}\n**Maç ID:** `{match_id}`\n**Harita:** {target_match['map']}",
            color=discord.Color(COLORS.SUCCESS)
        )
        
        embed.add_field(name="⚔️ Kills", value=str(kills), inline=True)
        embed.add_field(name="💀 Deaths", value=str(deaths), inline=True)
        embed.add_field(name="🤝 Assists", value=str(assists), inline=True)
        embed.add_field(name="📊 K/D", value=f"{round(kills/deaths, 2) if deaths > 0 else kills}", inline=True)
        
        await ctx.send(embed=embed)
        logger.info(f"Manual KDA added to match {match_id} for {player_name} by {ctx.author}")
    
    
    @commands.command(name='training_report', aliases=['tr'])
    async def training_report(self, ctx, match_id: str = None):
        """
        Training maçı raporu gösterir
        
        Kullanım: !training_report [match_id]
        Örnek: !training_report 1
        """
        db = self.load_training_db()
        
        if not db['matches']:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        # Match seç
        if match_id:
            match = None
            for m in db['matches']:
                if m['match_id'] == match_id:
                    match = m
                    break
            
            if not match:
                await ctx.send(f"❌ Maç ID `{match_id}` bulunamadı!")
                return
        else:
            # Son maçı göster
            match = db['matches'][-1]
        
        # Rapor oluştur
        embed = discord.Embed(
            title=f"📊 Training Maç Raporu - #{match['match_id']}",
            description=f"**Harita:** {match['map']}\n**Durum:** {match['status'].upper()}",
            color=discord.Color(COLORS.GOLD)
        )
        
        # Zaman bilgileri
        start_time = datetime.datetime.fromisoformat(match['start_time'])
        time_str = f"🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}"
        
        if match['end_time']:
            end_time = datetime.datetime.fromisoformat(match['end_time'])
            duration = end_time - start_time
            duration_mins = int(duration.total_seconds() / 60)
            time_str += f"\n⏱️ Süre: {duration_mins} dakika"
        
        embed.add_field(name="⏰ Zaman", value=time_str, inline=False)
        
        # Oyuncu istatistikleri
        if match['players']:
            # K/D'ye göre sırala
            sorted_players = sorted(match['players'], key=lambda p: p.get('kd_ratio', 0), reverse=True)
            
            player_stats = ""
            for i, player in enumerate(sorted_players[:10], 1):  # Top 10
                name = player['name'][:20]  # İsmi kısalt
                kills = player.get('final_kills', 0)
                deaths = player.get('final_deaths', 0)
                assists = player.get('final_assists', 0)
                kd = player.get('kd_ratio', 0)
                source = player.get('data_source', 'unknown')
                
                # Emoji badge
                source_emoji = "📊" if source == "delta" else "📸" if source == "manual" else "🔀"
                
                player_stats += f"**{i}.** {name}\n"
                player_stats += f"> {source_emoji} K:{kills} D:{deaths} A:{assists} | K/D: {kd:.2f}\n"
            
            embed.add_field(name="🏆 Oyuncu İstatistikleri", value=player_stats or "Henüz veri yok", inline=False)
        else:
            embed.add_field(name="🏆 Oyuncu İstatistikleri", value="Henüz oyuncu verisi eklenmemiş.\n`!training_kda_add` ile ekleyin.", inline=False)
        
        embed.add_field(
            name="📌 Veri Kaynakları",
            value="📊 Delta (Otomatik) | 📸 Manuel | 🔀 Hibrit",
            inline=False
        )
        
        embed.set_footer(text=f"Server: {match['server_ip']} | Toplam Maç: {len(db['matches'])}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='training_players', aliases=['tp'])
    async def training_players(self, ctx, match_id: str = None):
        """
        Maçtaki oyuncu katılım listesini gösterir (snapshot'tan)
        
        Kullanım: !training_players [match_id]
        Örnek: !training_players 4
        """
        db = self.load_training_db()
        
        if not db['matches']:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        # Match seç
        if match_id:
            match = None
            for m in db['matches']:
                if m['match_id'] == match_id:
                    match = m
                    break
            
            if not match:
                await ctx.send(f"❌ Maç ID `{match_id}` bulunamadı!")
                return
        else:
            # Son maçı göster
            match = db['matches'][-1]
        
        # Snapshot kontrolü
        snapshot_start = match.get('snapshot_start')
        snapshot_end = match.get('snapshot_end')
        existing_players = match.get('players', [])
        
        # Snapshot yoksa ama player data varsa, onu göster
        if not snapshot_start and not snapshot_end and not existing_players:
            await ctx.send(f"❌ Maç #{match['match_id']} için hiç veri yok! Manuel olarak `!training_kda_add_to {match['match_id']}` ile ekleyebilirsiniz.")
            return
        
        embed = discord.Embed(
            title=f"📋 Oyuncu Listesi - Maç #{match['match_id']}",
            description=f"**Harita:** {match['map']}\n**Durum:** {match['status'].upper()}",
            color=discord.Color(COLORS.INFO)
        )
        
        # Katılımcıları topla
        all_participants = {}
        
        # Snapshot varsa kullan
        if snapshot_start:
            for p in snapshot_start.get('players', []):
                steam_id = p['steam_id']
                all_participants[steam_id] = {
                    'name': p['name'],
                    'start': True,
                    'end': False
                }
        
        if snapshot_end:
            for p in snapshot_end.get('players', []):
                steam_id = p['steam_id']
                if steam_id in all_participants:
                    all_participants[steam_id]['end'] = True
                else:
                    all_participants[steam_id] = {
                        'name': p['name'],
                        'start': False,
                        'end': True
                    }
        
        # Snapshot yoksa existing players'dan al
        if not all_participants and existing_players:
            for p in existing_players:
                steam_id = p.get('steam_id', 'unknown')
                all_participants[steam_id] = {
                    'name': p.get('name', 'Unknown'),
                    'start': True,  # Var olduğu için True
                    'end': True
                }
        
        # Mevcut player data
        player_data_map = {p.get('steam_id'): p for p in existing_players}
        
        # Liste oluştur
        full_match_players = []  # Baştan sona oynayanlar
        partial_players = []  # Kısmi katılım
        
        for steam_id, info in all_participants.items():
            player_name = info['name'][:30]  # Kısalt
            
            # KDA durumu
            if steam_id in player_data_map:
                pd = player_data_map[steam_id]
                if pd.get('data_source') == 'pending':
                    status = "⏳ Bekliyor"
                elif pd.get('data_source') in ['manual', 'hybrid']:
                    k = pd.get('final_kills', 0)
                    d = pd.get('final_deaths', 0)
                    a = pd.get('final_assists', 0)
                    status = f"✅ K:{k} D:{d} A:{a}"
                else:
                    status = "⏳ Bekliyor"
            else:
                status = "⏳ Bekliyor"
            
            # Katılım durumu
            if info['start'] and info['end']:
                full_match_players.append(f"• {player_name} - {status}")
            else:
                join_status = "Katıldı" if not info['start'] else "Ayrıldı"
                partial_players.append(f"• {player_name} ({join_status})")
        
        # Embed'e ekle
        if full_match_players:
            # Sayfalama (max 1024 karakter per field)
            player_text = "\n".join(full_match_players)
            if len(player_text) > 1024:
                # İlk 15 oyuncu
                player_text = "\n".join(full_match_players[:15]) + f"\n... ve {len(full_match_players) - 15} oyuncu daha"
            
            embed.add_field(
                name=f"🎮 Katılımcılar ({len(full_match_players)} oyuncu)",
                value=player_text or "Yok",
                inline=False
            )
        
        if partial_players:
            partial_text = "\n".join(partial_players[:10])
            embed.add_field(
                name=f"⚠️ Kısmi Katılım ({len(partial_players)} oyuncu)",
                value=partial_text,
                inline=False
            )
        
        # KDA ekleme talimatı
        pending_count = sum(1 for sid in all_participants.keys() if sid not in player_data_map or player_data_map.get(sid, {}).get('data_source') == 'pending')
        
        if pending_count > 0:
            embed.add_field(
                name="📝 KDA Ekleme",
                value=f"**{pending_count}** oyuncu için KDA verisi bekleniyor.\n```!1training_kda_add_to {match['match_id']} \"İsim\" K D A```",
                inline=False
            )
        
        # Snapshot bilgisi
        snapshot_info = "✅ Snapshot var" if (snapshot_start or snapshot_end) else "📝 Manuel veri"
        embed.set_footer(text=f"Toplam: {len(all_participants)} | {snapshot_info} | ✅ = Veri Eklendi | ⏳ = Bekliyor")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='training_list', aliases=['tl'])
    async def training_list(self, ctx):
        """Tüm training maçlarını listeler"""
        db = self.load_training_db()
        
        if not db['matches']:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        embed = discord.Embed(
            title="📋 Training Maçları",
            description=f"Toplam {len(db['matches'])} maç kaydedildi",
            color=discord.Color(COLORS.INFO)
        )
        
        for match in db['matches'][-10:]:  # Son 10 maç
            status_emoji = "✅" if match['status'] == 'completed' else "⏳"
            player_count = len(match['players'])
            
            start_time = datetime.datetime.fromisoformat(match['start_time'])
            date_str = start_time.strftime('%d.%m.%Y %H:%M')
            
            value = f"**Harita:** {match['map']}\n**Tarih:** {date_str}\n**Oyuncular:** {player_count}"
            
            embed.add_field(
                name=f"{status_emoji} Maç #{match['match_id']}",
                value=value,
                inline=True
            )
        
        embed.set_footer(text="Detaylı rapor için: !training_report <match_id>")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TrainingMatches(bot))
