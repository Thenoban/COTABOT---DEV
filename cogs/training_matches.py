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

# Import custom exceptions
from exceptions import APIError, BattleMetricsAPIError, DataError, JSONParseError

# Database adapter
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.adapter import DatabaseAdapter

logger = logging.getLogger("TrainingMatches")


class TrainingMatches(commands.Cog):
    """Training maçlarını takip eden cog - Delta hesaplama ve manuel KDA girişi"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        # Database
        self.db = DatabaseAdapter('sqlite:///cotabot_dev.db')
        self.db.init_db()
        self.training_server_ip = "84.200.135.219:7789"
        self.active_match = None  # Will be loaded from DB
        
    async def cog_load(self):
        """Cog yüklendiğinde HTTP session oluştur ve aktif maçı kontrol et"""
        self.session = aiohttp.ClientSession()
        
        # Check for active match in DB
        active = await self.db.get_active_training_match()
        if active:
            self.active_match = active.id
            logger.info(f"Restored active match {self.active_match}")
        
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
                
        except BattleMetricsAPIError as e:
            logger.error(f"Error fetching BattleMetrics snapshot: {e}", exc_info=True)
            return None
    
    async def fetch_player_stats(self, steam_id: str) -> Optional[Dict]:
        """
        Database'den oyuncu istatistiklerini al
        """
        try:
            player = await self.db.get_player_by_steam_id(steam_id)
            if not player:
                return None
            
            # Map DB stats to legacy format if needed, or just return basic info
            # The cog seems to only need this to verify player exists or get name
            stats = {}
            if player.stats:
                s = player.stats
                stats = {
                    "totalScore": s.total_score,
                    "totalKills": s.total_kills,
                    "totalDeaths": s.total_deaths,
                    "totalRevives": s.total_revives,
                    "totalKdRatio": s.kd_ratio
                }
            
            return {
                'steam_id': player.steam_id,
                'name': player.name,
                'stats': stats,
                'season_stats': {} 
            }
            
        except Exception as e:
            logger.error(f"Error fetching player stats for {steam_id}: {e}", exc_info=True)
            return None
    
    async def find_steam_id_by_name(self, player_name: str) -> Optional[str]:
        """
        Database'den oyuncu ismine göre Steam ID bulur
        """
        try:
            player_name_lower = player_name.lower().strip()
            
            # Use search_players from adapter
            results = await self.db.search_players(player_name)
            
            # 1. Exact match
            for p in results:
                if p.name.lower().strip() == player_name_lower:
                    logger.info(f"Found exact match Steam ID {p.steam_id} for player {player_name}")
                    return p.steam_id
            
            # 2. First result if exists
            if results:
                logger.info(f"Found partial match Steam ID {results[0].steam_id} for player {player_name}")
                return results[0].steam_id
            
            logger.debug(f"No Steam ID found for player {player_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding Steam ID for {player_name}: {e}", exc_info=True)
            return None
    

    
    @commands.command(name='training_start', aliases=['ts'])
    async def training_start(self, ctx, *, map_name: str = "Unknown"):
        """
        Yeni bir training maçı başlatır ve snapshot alır
        """
        if not await self.check_permissions(ctx):
            return
        
        # Check active match (memory or DB)
        if self.active_match:
            await ctx.send("❌ Zaten aktif bir maç var! Önce `!training_end` ile bitirin.")
            return
        
        # Double check DB incase memory is out of sync
        active_db = await self.db.get_active_training_match()
        if active_db:
             self.active_match = active_db.id
             await ctx.send(f"❌ Veritabanında aktif bir maç bulundu (ID: {active_db.id})! Önce onu bitirin.")
             return
        
        await ctx.send("🎮 **Training maçı başlatılıyor...**")
        
        # Determine next Match ID
        # Get recent matches to find last ID
        recent = await self.db.get_training_matches(limit=1)
        next_id = 1
        if recent:
            last_id = recent[0]['match_id']
            if isinstance(last_id, int):
                next_id = last_id + 1
            elif isinstance(last_id, str) and last_id.isdigit():
                next_id = int(last_id) + 1
            else:
                next_id = 100 # Fallback
        
        match_id = next_id
        
        # Snapshot al
        snapshot = None
        snapshot_json = None
        from .utils.config import TRAINING_SERVER_ID
        if TRAINING_SERVER_ID:
            snapshot = await self.fetch_battlemetrics_snapshot(TRAINING_SERVER_ID)
            if snapshot:
                snapshot_json = json.dumps(snapshot)
                logger.info(f"Match {match_id} started with snapshot: {len(snapshot.get('players', []))} players")
        
        # Create match in DB
        try:
            await self.db.create_training_match(
                match_id=match_id,
                server_ip=self.training_server_ip,
                map_name=map_name,
                start_time=datetime.datetime.now()
            )
            
            # Update snapshot logic if needed, create_training_match didn't support snapshot arg 
            # so we might need a quick update call or modify create_training_match
            # My create_training_match adapter didn't accept snapshot_start. 
            # I should call update_training_match immediately to save snapshot.
            if snapshot_json:
                await self.db.update_training_match(match_id=match_id, snapshot_start=snapshot_json)
            
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
            
        except Exception as e:
            logger.error(f"Failed to start match: {e}", exc_info=True)
            await ctx.send(f"❌ Maç başlatılırken hata oluştu: {e}")
    
    @commands.command(name='training_end', aliases=['te'])
    async def training_end(self, ctx):
        """
        Aktif training maçını sonlandırır ve delta hesaplar
        """
        if not await self.check_permissions(ctx):
            return
        
        if not self.active_match:
            # Check DB just in case
            active_db = await self.db.get_active_training_match()
            if active_db:
                self.active_match = active_db.id
            else:
                await ctx.send("❌ Aktif bir maç yok! `!training_start` ile maç başlatın.")
                return
        
        await ctx.send("⏱️ **Training maçı sonlandırılıyor...**")
        
        match_id = self.active_match
        
        # Snapshot al
        snapshot_end = None
        snapshot_end_json = None
        from .utils.config import TRAINING_SERVER_ID
        if TRAINING_SERVER_ID:
            snapshot_end = await self.fetch_battlemetrics_snapshot(TRAINING_SERVER_ID)
            if snapshot_end:
                snapshot_end_json = json.dumps(snapshot_end)
        
        # Maçı kapat
        end_time = datetime.datetime.now()
        await self.db.update_training_match(
            match_id=match_id,
            status='completed',
            end_time=end_time,
            snapshot_end=snapshot_end_json
        )
        
        # Delta calculation logic - simplified for DB
        # Retrieve start snapshot from DB if logic requires it
        # Actually calculate_delta operates on 'match' dict.
        # We can reconstruct a simple match dict for it OR refactor it.
        # For simplicity, let's reuse logic by fetching details.
        
        # Get match details just to get snapshot_start
        # (This is a bit inefficient but safe)
        matches = await self.db.get_training_matches(limit=1, status='completed') # Should be this one usually
        # Actually get by ID or status might not index well.
        # Let's just trust we have snapshot_end players and add them as placeholders
        
        if snapshot_end:
             # Add all present players as pending
             count = 0
             for p in snapshot_end.get('players', []):
                 await self.db.add_training_player(match_id, {
                     'steam_id': p['steam_id'],
                     'name': p['name'],
                     'data_source': 'pending'
                 })
                 count += 1
             logger.info(f"Added {count} pending players to match {match_id}")
        
        self.active_match = None
        
        embed = discord.Embed(
            title="🏁 Training Maçı Bitti!",
            description=f"**Maç ID:** `{match_id}`\n**Durum:** Completed",
            color=discord.Color(COLORS.GOLD)
        )
        
        embed.add_field(
            name="📊 Sonraki Adımlar",
            value=f"• Ekran görüntüsünden KDA eklemek için: `!training_kda_add`\n• Rapor görmek için: `!training_report {match_id}`",
            inline=False
        )
        
        await ctx.send(embed=embed)
        logger.info(f"Training match {match_id} ended by {ctx.author}")
    
    @commands.command(name='training_kda_add', aliases=['tka'])
    async def training_kda_add(self, ctx, player_name: str, kills: int, deaths: int, assists: int = 0):
        """
        Manuel KDA verisi ekler (fotoğraftan)
        """
        if not await self.check_permissions(ctx):
            return
        
        # Son tamamlanan maçı bul
        matches = await self.db.get_training_matches(limit=1)
        
        if not matches:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        # Son maçı al
        last_match = matches[0]
        match_id = last_match['match_id']
        
        # Oyuncu isminden Steam ID bul
        steam_id = await self.find_steam_id_by_name(player_name)
        if not steam_id:
            steam_id = 'unknown'
            logger.info(f"Steam ID not found for {player_name}, using 'unknown'")
        
        # Calculate KD
        kd = round(kills / deaths, 2) if deaths > 0 else kills
        
        # Add to DB
        await self.db.add_training_player(match_id, {
            'steam_id': steam_id,
            'name': player_name,
            'kills_manual': kills,
            'deaths_manual': deaths,
            'assists_manual': assists,
            'final_kills': kills,
            'final_deaths': deaths,
            'final_assists': assists,
            'kd_ratio': kd,
            'data_source': 'manual'
        })
        
        embed = discord.Embed(
            title="✅ KDA Eklendi",
            description=f"**Oyuncu:** {player_name}\n**Maç:** `{match_id}`",
            color=discord.Color(COLORS.SUCCESS)
        )
        
        embed.add_field(name="⚔️ Kills", value=str(kills), inline=True)
        embed.add_field(name="💀 Deaths", value=str(deaths), inline=True)
        embed.add_field(name="🤝 Assists", value=str(assists), inline=True)
        embed.add_field(name="📊 K/D", value=f"{kd}", inline=True)
        
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
        """
        match = None
        
        if match_id:
            # Try to find specific match
            # Since adapter only has 'get_training_matches' (recent), we fetch more
            matches = await self.db.get_training_matches(limit=50)
            match = next((m for m in matches if str(m['match_id']) == str(match_id)), None)
            
            if not match:
                await ctx.send(f"❌ Maç ID `{match_id}` bulunamadı! (Son 50 maç içinde aranır)")
                return
        else:
            # Last match
            matches = await self.db.get_training_matches(limit=1)
            if not matches:
                await ctx.send("❌ Henüz hiç maç kaydı yok!")
                return
            match = matches[0]
            
        # Rapor oluştur
        status_text = match['status'].upper() if match['status'] else 'UNKNOWN'
        embed = discord.Embed(
            title=f"📊 Training Maç Raporu - #{match['match_id']}",
            description=f"**Harita:** {match['map_name']}\n**Durum:** {status_text}",
            color=discord.Color(COLORS.GOLD)
        )
        
        # Zaman bilgileri
        time_str = "Unknown time"
        if match['start_time']:
            start_time = datetime.datetime.fromisoformat(match['start_time'])
            time_str = f"🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}"
            
            if match['end_time']:
                end_time = datetime.datetime.fromisoformat(match['end_time'])
                duration = end_time - start_time
                duration_mins = int(duration.total_seconds() / 60)
                time_str += f"\n⏱️ Süre: {duration_mins} dakika"
        
        embed.add_field(name="⏰ Zaman", value=time_str, inline=False)
        
        # Oyuncu istatistikleri
        players = match.get('players', [])
        if players:
            # K/D'ye göre sırala (KD float or int)
            sorted_players = sorted(players, key=lambda p: float(p.get('kd_ratio', 0) or 0), reverse=True)
            
            player_stats = ""
            for i, player in enumerate(sorted_players[:10], 1):  # Top 10
                name = player['name'][:20] if player['name'] else "Unknown"
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
        
        embed.set_footer(text=f"Server: {match['server_ip']}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='training_players', aliases=['tp'])
    async def training_players(self, ctx, match_id: str = None):
        """
        Maçtaki oyuncu katılım listesini gösterir
        """
        match = None
        
        if match_id:
             matches = await self.db.get_training_matches(limit=50)
             match = next((m for m in matches if str(m['match_id']) == str(match_id)), None)
             if not match:
                await ctx.send(f"❌ Maç ID `{match_id}` bulunamadı!")
                return
        else:
             matches = await self.db.get_training_matches(limit=1)
             if not matches:
                await ctx.send("❌ Henüz hiç maç kaydı yok!")
                return
             match = matches[0]
        
        status_text = match['status'].upper() if match['status'] else 'UNKNOWN'
        
        embed = discord.Embed(
            title=f"📋 Oyuncu Listesi - Maç #{match['match_id']}",
            description=f"**Harita:** {match['map_name']}\n**Durum:** {status_text}",
            color=discord.Color(COLORS.INFO)
        )
        
        # List DB players
        full_match_players = []
        for p in match.get('players', []):
            name = p['name']
            source = p.get('data_source')
            if source == 'pending':
                status = "⏳ Bekliyor"
            else:
                 k = p.get('final_kills', 0)
                 d = p.get('final_deaths', 0)
                 a = p.get('final_assists', 0)
                 status = f"✅ K:{k} D:{d} A:{a}"
            full_match_players.append(f"• {name} - {status}")
            
        if full_match_players:
             player_text = "\n".join(full_match_players)
             if len(player_text) > 1024:
                player_text = "\n".join(full_match_players[:15]) + f"\n... ve {len(full_match_players) - 15} oyuncu daha"
             
             embed.add_field(
                name=f"🎮 Katılımcılar ({len(full_match_players)} oyuncu)",
                value=player_text,
                inline=False
             )
        else:
             embed.add_field(name="Bilgi", value="Kayıtlı oyuncu yok.")
        
        await ctx.send(embed=embed)
        
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
        matches = await self.db.get_training_matches(limit=10)
        
        if not matches:
            await ctx.send("❌ Henüz hiç maç kaydı yok!")
            return
        
        embed = discord.Embed(
            title="📋 Training Maçları",
            description=f"Son {len(matches)} maç gösteriliyor",
            color=discord.Color(COLORS.INFO)
        )
        
        for match in matches:
            status = match['status']
            status_emoji = "✅" if status == 'completed' else "⏳"
            player_count = len(match.get('players', []))
            
            start_time_str = "Unknown"
            if match['start_time']:
                try:
                    dt = datetime.datetime.fromisoformat(match['start_time'])
                    start_time_str = dt.strftime('%d.%m.%Y %H:%M')
                except ValueError:
                    start_time_str = str(match['start_time'])
            
            map_name = match.get('map_name', 'Unknown')
            
            value = f"**Harita:** {map_name}\n**Tarih:** {start_time_str}\n**Oyuncular:** {player_count}"
            
            embed.add_field(
                name=f"{status_emoji} Maç #{match['match_id']}",
                value=value,
                inline=True
            )
        
        embed.set_footer(text="Detaylı rapor için: !training_report <match_id>")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TrainingMatches(bot))
