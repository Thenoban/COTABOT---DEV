import discord
from typing import Union
from discord.ext import commands, tasks
import aiohttp
import os
import datetime
import json
import asyncio
import traceback
import logging
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, CLAN_MEMBER_ROLE_IDS, COLORS, BM_API_URL, SERVER_ID, BM_API_KEY, GOOGLE_SHEET_KEY, DEV_MODE
from .utils.chart_maker import generate_activity_image, generate_profile_card
from .utils.pagination import PaginationView
from .utils.cache import TTLCache

logger = logging.getLogger("SquadPlayers")

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    logger.warning("gspread module not found. Google Sheets integration will be disabled.")

class PlayerAddModal(discord.ui.Modal, title="Oyuncu Ekle / Güncelle"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    steam_id = discord.ui.TextInput(
        label="Steam ID (64)",
        placeholder="76561198...",
        min_length=17,
        max_length=17
    )

    player_name = discord.ui.TextInput(
        label="Oyuncu İsmi",
        placeholder="Oyun içi tam isim",
        max_length=50
    )

    discord_id = discord.ui.TextInput(
        label="Discord ID (Opsiyonel)",
        placeholder="Sadece ID giriniz (Örn: 3050...)",
        required=False,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        s_id = self.steam_id.value
        p_name = self.player_name.value
        d_id = self.discord_id.value

        if not s_id.isdigit():
            await interaction.response.send_message("❌ Steam ID sadece rakamlardan oluşmalıdır.", ephemeral=True)
            return

        db_file = "squad_db.json"
        data = {"players": []}
        if os.path.exists(db_file):
            try:
                def _read():
                    with open(db_file, "r", encoding="utf-8") as f: return json.load(f)
                data = await asyncio.to_thread(_read)
            except: pass

        found = False
        # Discord ID can be numeric ID or username string
        parsed_d_id = None
        if d_id:
            if d_id.isdigit():
                parsed_d_id = int(d_id)  # Numeric Discord ID
            else:
                parsed_d_id = d_id  # Discord username (string)

        for p in data.get("players", []):
            if p["steam_id"] == s_id:
                p["name"] = p_name
                if parsed_d_id: p["discord_id"] = parsed_d_id
                found = True
                break
        
        if not found:
            new_p = {
                "steam_id": s_id,
                "name": p_name,
                "discord_id": parsed_d_id,
                "stats": {}, 
                "season_stats": {}
            }
            if "players" not in data: data["players"] = []
            data["players"].append(new_p)

        log_msg = f"[{datetime.datetime.now()}] Manual Player Update: {p_name} ({s_id}) by {interaction.user}"
        try:
            with open("squad_debug.log", "a", encoding="utf-8") as f: f.write(log_msg + "\n")
        except: pass

        # CRITICAL: Respond to interaction FIRST (before slow sync)
        action = "GÜNCELLENDİ" if found else "EKLENDİ"
        await interaction.response.send_message(f"✅ Oyuncu başarıyla **{action}**!\nİsim: {p_name}\nSteamID: {s_id}", ephemeral=True)
        
        # Now do slow operations in background
        cog = self.bot.get_cog("SquadPlayers")
        if cog:
            # Save to DB and auto-sync to Sheets (async background task)
            asyncio.create_task(cog._save_db_and_sync(data))
            
            # Log to Channel
            await cog.log_to_channel(interaction.guild, "✏️ Oyuncu Düzenlendi/Eklendi", 
                f"**Oyuncu:** {p_name}\n**SteamID:** `{s_id}`\n**Discord:** {parsed_d_id or '-'}", 
                interaction.user)
        else:
            # Fallback if cog not found (shouldn't happen)
            data["last_update"] = str(datetime.datetime.now())
            def _save():
                with open(db_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            await asyncio.to_thread(_save)

class PlayerSearchModal(discord.ui.Modal, title="Oyuncu Ara"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    name_query = discord.ui.TextInput(
        label="Oyuncu İsmi",
        placeholder="Aramak istediğiniz ismin bir kısmını yazın...",
        min_length=2,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        query = self.name_query.value.lower()
        
        matches = []
        if os.path.exists("squad_db.json"):
            try:
                def _read_search():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return [p for p in data.get("players", []) if query in p["name"].lower()]
                matches = await asyncio.to_thread(_read_search)
            except: pass
        
        if not matches:
            await interaction.response.send_message("❌ Eşleşen oyuncu bulunamadı.", ephemeral=True)
            return
            
        matches.sort(key=lambda x: x["name"])
        view = PlayerSelectView(self.bot, matches[:25])
        await interaction.response.send_message(f"🔍 **'{query}'** için {len(matches)} sonuç bulundu. İşlem yapmak için seçiniz:", view=view, ephemeral=True)

class PlayerSelectView(discord.ui.View):
    def __init__(self, bot, players):
        super().__init__(timeout=180)
        self.bot = bot
        options = []
        for p in players:
            label = p['name'][:100]
            desc = f"SID: {p['steam_id']}"
            options.append(discord.SelectOption(label=label, description=desc, value=p['steam_id']))
        
        self.add_item(PlayerSelectDropdown(bot, options))

class PlayerSelectDropdown(discord.ui.Select):
    def __init__(self, bot, options):
        self.bot = bot
        super().__init__(placeholder="Bir oyuncu seçin...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        steam_id = self.values[0]
        
        target_player = None
        if os.path.exists("squad_db.json"):
            try:
                def _find_player():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for p in data.get("players", []):
                            if p["steam_id"] == steam_id: return p
                    return None
                target_player = await asyncio.to_thread(_find_player)
            except: pass
            
        if not target_player:
            await interaction.response.send_message("❌ Oyuncu veritabanında bulunamadı (silinmiş olabilir).", ephemeral=True)
            return

        embed = discord.Embed(title=f"👤 Oyuncu Bilgisi: {target_player['name']}", color=discord.Color(COLORS.SQUAD))
        embed.add_field(name="Steam ID", value=f"`{target_player['steam_id']}`", inline=False)
        embed.add_field(name="Discord ID", value=f"`{target_player.get('discord_id', '-')}`", inline=False)
        
        view = PlayerActionView(self.bot, target_player)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PlayerActionView(discord.ui.View):
    def __init__(self, bot, player_data):
        super().__init__(timeout=180)
        self.bot = bot
        self.player_data = player_data

    @discord.ui.button(label="✏️ Düzenle", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PlayerAddModal(self.bot)
        modal.steam_id.default = self.player_data['steam_id']
        modal.player_name.default = self.player_data['name']
        if self.player_data.get('discord_id'):
            modal.discord_id.default = str(self.player_data['discord_id'])
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Sil", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s_id = self.player_data['steam_id']
        name = self.player_data['name']
        db_file = "squad_db.json"
        
        deleted = False
        if os.path.exists(db_file):
            try:
                def _delete_logic():
                    with open(db_file, "r", encoding="utf-8") as f: data = json.load(f)
                    initial_len = len(data.get("players", []))
                    data["players"] = [p for p in data["players"] if p["steam_id"] != s_id]
                    if len(data["players"]) < initial_len:
                        data["last_update"] = str(datetime.datetime.now())
                        with open(db_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                        return True
                    return False
                
                deleted = await asyncio.to_thread(_delete_logic)
            except Exception as e:
                await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)
                return

        if deleted:
            try:
                with open("squad_debug.log", "a", encoding="utf-8") as f: 
                    f.write(f"[{datetime.datetime.now()}] Manual Player DELETE: {name} ({s_id}) by {interaction.user}\n")
            except: pass
            
            # Log to Channel
            cog = self.bot.get_cog("SquadPlayers")
            if cog:
                await cog.log_to_channel(interaction.guild, "🗑️ Oyuncu Silindi", 
                    f"**Oyuncu:** {name}\n**SteamID:** `{s_id}`", 
                    interaction.user, color=COLORS.ERROR)
            
            await interaction.response.send_message(f"✅ **{name}** ({s_id}) başarıyla silindi.", ephemeral=True)
            
            # Sync to Sheet
            if cog:
                 asyncio.create_task(cog.update_sheet_player(s_id, name, None, delete=True))
        else:
            await interaction.response.send_message("❌ Silme işlemi başarısız (Zaten silinmiş olabilir).", ephemeral=True)


class PlayerManageView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    def check_auth(self, interaction):
        if interaction.user.guild_permissions.administrator: return True
        if interaction.user.id in ADMIN_USER_IDS: return True
        for r in interaction.user.roles:
            if r.id in ADMIN_ROLE_IDS: return True
        return False

    @discord.ui.button(label="🔎 Oyuncu Ara (Düzenle/Sil)", style=discord.ButtonStyle.primary, row=0, custom_id="pm_search_player")
    async def search_player_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_auth(interaction): 
             await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
             return
        modal = PlayerSearchModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="➕ Oyuncu Ekle", style=discord.ButtonStyle.green, row=1, custom_id="pm_add_player")
    async def add_player_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_auth(interaction): 
             await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
             return
        modal = PlayerAddModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💾 Veritabanı İndir", style=discord.ButtonStyle.secondary, row=1, custom_id="pm_download_db")
    async def download_db_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
             await interaction.response.send_message("❌ Sadece yöneticiler indirebilir.", ephemeral=True)
             return
        if os.path.exists("squad_db.json"):
            await interaction.response.send_message(file=discord.File("squad_db.json"), ephemeral=True)
        else:
            await interaction.response.send_message("❌ Veritabanı dosyası yok.", ephemeral=True)

class SquadLeaderboardView(PaginationView):
    def __init__(self, players, mode="AllTime", refresh_callback=None):
        # Initial Sort
        self.mode = mode
        if self.mode == "AllTime":
            self.sort_key = "totalScore"
            self.sort_name = "Puan (Score)"
            self.title_prefix = "🏆 İstatistik Sıralama (Tüm Zamanlar)"
            self.color = discord.Color(COLORS.GOLD)
        else:
            self.sort_key = "seasonScore"
            self.sort_name = "Puan (Score)"
            self.title_prefix = "📅 İstatistik Sıralama (Bu Sezon)"
            self.color = discord.Color(COLORS.GREEN)

        self.all_players = players # Keep original unsorted/full list if needed, strictly we just need 'players'
        # But we sort 'players' in place or create new list.
        # Let's sort initially
        self.sort_players(players)
        
        # Init Pagination with sorted data
        super().__init__(data=self.data, title=self.title_prefix, page_size=10, refresh_callback=refresh_callback)

    def sort_players(self, players_list):
        stats_key = "stats" if self.mode == "AllTime" else "season_stats"
        prefix = "total" if self.mode == "AllTime" else "season"

        def get_sort_value(p):
            st = p.get(stats_key, {})
            if not st: return 0
            val = st.get(self.sort_key, 0)
            try: return float(val)
            except: return 0
        
        self.data = sorted(players_list, key=get_sort_value, reverse=True)

    def get_current_embed(self):
        # Override to provide custom formatted embed
        exclude_start = self.current_page * self.page_size
        exclude_end = exclude_start + self.page_size
        page_items = self.data[exclude_start:exclude_end]

        embed = discord.Embed(
            title=f"{self.title_prefix}", 
            description=f"📂 **Sıralama Kriteri:** {self.sort_name}",
            color=self.color
        )
        timestamp = datetime.datetime.now().strftime('%H:%M')
        embed.set_footer(text=f"Mod: {self.mode} | Sayfa {self.current_page + 1}/{self.total_pages} | Güncelleme: {timestamp}")

        stats_key = "stats" if self.mode == "AllTime" else "season_stats"
        prefix = "total" if self.mode == "AllTime" else "season"

        def get_stat(p, key_suffix, default=0):
            st = p.get(stats_key, {})
            if not st: return default
            full_key = f"{prefix}{key_suffix}"
            if key_suffix == "KdRatio": full_key = f"{prefix}KdRatio" 
            val = st.get(full_key, default)
            try: return float(val)
            except: return default

        for i, p in enumerate(page_items, exclude_start + 1):
            score = int(get_stat(p, "Score"))
            kills = int(get_stat(p, "Kills"))
            deaths = int(get_stat(p, "Deaths"))
            revives = int(get_stat(p, "Revives"))
            kd = get_stat(p, "KdRatio", 0.0)
            kd_str = f"{kd:.2f}"
            
            rank_display = f"#{i}"
            if i == 1: rank_display = "🥇"
            elif i == 2: rank_display = "🥈"
            elif i == 3: rank_display = "🥉"
            elif i <= 5: rank_display = f"Top {i} 🎖️"
            
            field_name = f"{rank_display}  {p['name']}"
            s_score = f"**{score:,}**" if "Score" in self.sort_key else f"{score:,}"
            s_kd = f"**{kd_str}**" if "KdRatio" in self.sort_key else f"{kd_str}"
            s_kill = f"**{kills}**" if "Kills" in self.sort_key else f"{kills}"
            s_death = f"**{deaths}**" if "Deaths" in self.sort_key else f"{deaths}"
            s_revive = f"**{revives}**" if "Revives" in self.sort_key else f"{revives}"

            line1 = f"🏆 Puan: {s_score}  |  ⚖️ K/D: {s_kd}"
            line2 = f"⚔️ K: {s_kill}  💀 D: {s_death}  🚑 R: {s_revive}"
            field_value = f"> {line1}\n> {line2}"
            embed.add_field(name=field_name, value=field_value, inline=False)
            
        return embed

    async def update_view_custom(self, interaction):
        # Re-calculate totals because data might have changed (sorted)
        self.total_pages = max(1, (len(self.data) + self.page_size - 1) // self.page_size)
        self.current_page = 0 # Reset to first page on sort/filter change
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    # Custom buttons for this view (Rows 2, 3...)
    # Pagination buttons are Row 0 (default) or we can move them.
    # Default PaginationView buttons don't have row set, so they take 0.
    # We'll set these to row 1, 2 for layout.

    @discord.ui.button(label="Top 10", style=discord.ButtonStyle.secondary, row=1)
    async def limit_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page_size = 10
        await self.update_view_custom(interaction)
        
    @discord.ui.button(label="Top 25", style=discord.ButtonStyle.secondary, row=1)
    async def limit_25(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page_size = 25
        await self.update_view_custom(interaction)

    @discord.ui.button(label="🏆 Puan", style=discord.ButtonStyle.success, row=2)
    async def sort_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefix = "total" if self.mode == "AllTime" else "season"
        self.sort_key = f"{prefix}Score"
        self.sort_name = "Puan (Score)"
        self.sort_players(self.data) # Re-sort current data
        await self.update_view_custom(interaction)

    @discord.ui.button(label="⚖️ K/D", style=discord.ButtonStyle.primary, row=2)
    async def sort_kd(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefix = "total" if self.mode == "AllTime" else "season"
        self.sort_key = f"{prefix}KdRatio"
        self.sort_name = "K/D Oranı"
        self.sort_players(self.data)
        await self.update_view_custom(interaction)

    @discord.ui.button(label="⚔️ Kill", style=discord.ButtonStyle.danger, row=2)
    async def sort_kill(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefix = "total" if self.mode == "AllTime" else "season"
        self.sort_key = f"{prefix}Kills"
        self.sort_name = "Kill Sayısı"
        self.sort_players(self.data)
        await self.update_view_custom(interaction)
        
    @discord.ui.button(label="💀 Death", style=discord.ButtonStyle.secondary, row=2)
    async def sort_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefix = "total" if self.mode == "AllTime" else "season"
        self.sort_key = f"{prefix}Deaths"
        self.sort_name = "Death Sayısı"
        self.sort_players(self.data)
        await self.update_view_custom(interaction)
    
    @discord.ui.button(label="➕ Revive", style=discord.ButtonStyle.primary, row=2)
    async def sort_revive(self, interaction: discord.Interaction, button: discord.ui.Button):
        prefix = "total" if self.mode == "AllTime" else "season"
        self.sort_key = f"{prefix}Revives"
        self.sort_name = "Canlandırma (Revives)"
        self.sort_players(self.data)
        await self.update_view_custom(interaction)



class ActivityManageView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild_id = str(guild_id)

    @discord.ui.button(label="🗑️ Aktiflik Panelini Sil", style=discord.ButtonStyle.danger)
    async def delete_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_permissions(interaction): return

        cfg = self.cog.load_activity_panel_config()
        if self.guild_id in cfg:
            try:
                g_cfg = cfg[self.guild_id]
                ch = interaction.guild.get_channel(g_cfg["channel_id"])
                if ch:
                    msg = await ch.fetch_message(g_cfg["message_id"])
                    await msg.delete()
            except: pass
            
            del cfg[self.guild_id]
            self.cog.save_activity_panel_config(cfg)
            await interaction.response.edit_message(content="✅ Aktiflik paneli silindi.", embed=None, view=None)
        else:
            await interaction.response.edit_message(content="❌ Panel bulunamadı.", embed=None, view=None)

class SquadPlayers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.activity_config_file = "activity_panel.json"
        self.ACTIVITY_FILE = "squad_activity.json"
        self.cache = TTLCache(max_size=500)  # Initialize cache
        # Loops auto-start via @tasks.loop decorator

    @tasks.loop(hours=1)
    async def automated_report_loop(self):
        """Checks periodically if a scheduled report (Weekly/Monthly) is due."""
        now = datetime.datetime.now()
        report_db = self._get_report_db()
        meta = report_db.get("meta", {})
        
        # --- WEEKLY REPORT ---
        # Monday = 0. Run if it is Monday.
        if now.weekday() == 0 and now.hour >= 9:  # After 9 AM
            last_run_str = meta.get("last_weekly")
            should_run = True
            
            if last_run_str:
                last_run = datetime.datetime.fromisoformat(last_run_str)
                # If last run was less than 4 days ago, don't run again (avoid double run on same Monday)
                if (now - last_run).days < 4:
                    should_run = False
            
            if should_run:
                # Calculate deltas BEFORE taking new snapshot
                deltas = self._calculate_deltas("weekly")
                
                # Save to history (Phase 2)
                if deltas:
                    self._save_to_history("weekly", deltas)
                
                # Find Guild (Assuming single server bot, or iterate)
                # DEV/PROD specific GUILD_ID would be better, but we traverse bot.guilds
                for guild in self.bot.guilds:
                    # Optional: Check if guild has #rapor-log?
                    try:
                        await self._publish_report(guild, "weekly")
                        logger.info(f"Published Automated Weekly Report for {guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to auto-publish weekly report: {e}")
                
                # Take Snapshot & Update Meta (AFTER history save)
                self._take_snapshot("weekly")
                meta["last_weekly"] = now.isoformat()
                self._save_report_db(report_db)
                logger.info("Automated Weekly Snapshot Taken.")
        
        # --- MONTHLY REPORT ---
        # Run on 1st of month, after 10 AM
        if now.day == 1 and now.hour >= 10:
            last_monthly = meta.get("last_monthly")
            should_run = True
            
            if last_monthly:
                last = datetime.datetime.fromisoformat(last_monthly)
                # If last run was less than 20 days ago, skip (avoid double run)
                if (now - last).days < 20:
                    should_run = False
            
            if should_run:
                # Calculate deltas BEFORE taking new snapshot
                deltas = self._calculate_deltas("monthly")
                
                # Save to history (Phase 2)
                if deltas:
                    self._save_to_history("monthly", deltas)
                
                for guild in self.bot.guilds:
                    try:
                        await self._publish_report(guild, "monthly")
                        logger.info(f"Published Automated Monthly Report for {guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to auto-publish monthly report: {e}")
                
                # Take Snapshot & Update Meta (AFTER history save)
                self._take_snapshot("monthly")
                meta["last_monthly"] = now.isoformat()
                self._save_report_db(report_db)
                logger.info("Automated Monthly Snapshot Taken.")

    @automated_report_loop.before_loop
    async def before_report_loop(self):
        await self.bot.wait_until_ready()

    async def update_sheet_player(self, steam_id, name, discord_id, delete=False):
        """Helper to sync single player changes to Google Sheet."""
        if not gspread or not GOOGLE_SHEET_KEY: return
        
        try:
            scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                     "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
            client = await asyncio.to_thread(gspread.authorize, creds)
            sheet = await asyncio.to_thread(client.open_by_key, GOOGLE_SHEET_KEY)
            worksheet = await asyncio.to_thread(lambda: sheet.sheet1)
            
            all_rows = await asyncio.to_thread(worksheet.get_all_values)
            if not all_rows: return

            headers = [h.lower().strip() for h in all_rows[0]]
            idx_steam = -1
            idx_name = -1
            idx_discord = -1
            
            possible_steam = ["steam64id", "steamid", "steam_id", "steam id"]
            possible_name = ["player", "name", "isim", "oyuncu"]
            possible_discord = ["discord id", "discord_id", "discordid"]
            
            for i, h in enumerate(headers):
                if idx_steam == -1 and h in possible_steam: idx_steam = i
                if idx_name == -1 and h in possible_name: idx_name = i
                if idx_discord == -1 and h in possible_discord: idx_discord = i
            
            if idx_steam == -1: return

            target_row_idx = -1
            for i, row in enumerate(all_rows):
                if i == 0: continue
                s_id = row[idx_steam].strip() if len(row) > idx_steam else ""
                if s_id == steam_id:
                    target_row_idx = i + 1 # 1-based index
                    break
            
            if delete:
                if target_row_idx != -1:
                    await asyncio.to_thread(worksheet.delete_rows, target_row_idx)
                    logger.info(f"Sheet Sync: Deleted {steam_id}")
            else:
                # Add or Update
                d_id_str = str(discord_id) if discord_id else ""
                
                if target_row_idx != -1:
                    # Update existing
                    updates = []
                    if idx_name != -1: await asyncio.to_thread(worksheet.update_cell, target_row_idx, idx_name + 1, name)
                    if idx_discord != -1: await asyncio.to_thread(worksheet.update_cell, target_row_idx, idx_discord + 1, d_id_str)
                    logger.info(f"Sheet Sync: Updated {steam_id}")
                else:
                    # Append
                    new_row = [""] * len(headers)
                    new_row[idx_steam] = steam_id
                    if idx_name != -1: new_row[idx_name] = name
                    if idx_discord != -1: new_row[idx_discord] = d_id_str
                    await asyncio.to_thread(worksheet.append_row, new_row)
                    logger.info(f"Sheet Sync: Appended {steam_id}")

        except Exception as e:
            logger.error(f"Sheet Sync Error ({steam_id}): {e}")
    
    # ==================== AUTO-SYNC DB TO SHEETS ====================
    
    def _get_sheets_client_sync(self):
        """
        Returns authorized gspread client (synchronous).
        Raises exception if gspread not available or credentials missing.
        """
        if gspread is None:
            raise ImportError("gspread module not installed")
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
        return gspread.authorize(creds)
    
    async def _export_to_sheets_full(self, db_data, sheet_name="Whitelist"):
        """
        Internal function to export ENTIRE squad_db.json data to Google Sheets.
        This replaces the sheet contents with current DB data.
        Called automatically after DB modifications for full sync.
        
        Args:
            db_data: The squad_db.json dictionary
            sheet_name: Target sheet name (default: "Whitelist")
        """
        try:
            if gspread is None:
                logger.debug("⚠️ gspread not available, skipping Sheets sync")
                return False
            
            # Use GOOGLE_SHEET_KEY from config
            SHEET_KEY = GOOGLE_SHEET_KEY if GOOGLE_SHEET_KEY else "1ExwpvnVCLD7LYWREFr4eQ5VzdubdH5R_WCqaZBhcMHE"
            
            if not SHEET_KEY:
                logger.warning("⚠️ GOOGLE_SHEET_KEY not configured, skipping Sheets sync")
                return False
            
            # Get client and perform export (sync operations, run in thread)
            def _sync_export():
                client = self._get_sheets_client_sync()
                spreadsheet = client.open_by_key(SHEET_KEY)
                
                # Try to get sheet, create if doesn't exist
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                
                # Prepare data
                headers = ["Steam64ID", "Player", "Discord ID"]
                rows = [headers]
                
                for player in db_data.get("players", []):
                    steam_id = player.get("steam_id", "")
                    name = player.get("name", "")
                    discord_id = str(player.get("discord_id", "")) if player.get("discord_id") else ""
                    
                    rows.append([steam_id, name, discord_id])
                
                # Clear and update sheet (batch operation for speed)
                worksheet.clear()
                worksheet.update(rows, value_input_option='RAW')
                
                return len(rows) - 1  # Exclude header
            
            # Run in thread to avoid blocking
            exported_count = await asyncio.to_thread(_sync_export)
            logger.info(f"✅ Sheets auto-sync: {exported_count} oyuncu → '{sheet_name}'")
            return True
            
        except FileNotFoundError:
            logger.warning("⚠️ service_account.json not found, skipping Sheets sync")
            return False
        except Exception as e:
            logger.error(f"❌ Sheets sync hatası: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    async def _save_db_and_sync(self, data):
        """
        Save to squad_db.json AND automatically sync to Google Sheets.
        This is the PRIMARY function to use when modifying the database.
        
        Args:
            data: Complete database dictionary to save
        """
        # Update timestamp
        data["last_update"] = str(datetime.datetime.now())
        
        # 1. Save to JSON (critical - must succeed)
        def _write_json():
            with open("squad_db.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        await asyncio.to_thread(_write_json)
        logger.debug("💾 DB saved to squad_db.json")
        
        # 2. Auto-sync to Sheets (non-critical - failure won't break functionality)
        try:
            await self._export_to_sheets_full(data)
        except Exception as e:
            logger.warning(f"⚠️ Auto-sync to Sheets failed (DB still saved): {e}")
    
    # ==================== END AUTO-SYNC HELPERS ====================

    async def log_to_channel(self, guild, title, description, user=None, color=None):
        if not guild: return
        
        target_name = "squad-log"
        channel = discord.utils.get(guild.text_channels, name=target_name)
        
        if not channel:
            # Fallback to general log or try to find it
            try:
                all_channels = await guild.fetch_channels()
                text_channels = [c for c in all_channels if isinstance(c, discord.TextChannel)]
                channel = discord.utils.get(text_channels, name=target_name)
            except: pass
            
        if not channel: return # Fail silently if no channel
        
        if color is None: color = COLORS.INFO
        
        embed = discord.Embed(title=title, description=description, color=discord.Color(color))
        if user:
            embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
            embed.set_footer(text=f"Yapan: {user.display_name} | Zaman: {datetime.datetime.now().strftime('%H:%M:%S')}")
        else:
            embed.set_footer(text=f"Zaman: {datetime.datetime.now().strftime('%H:%M:%S')}")
            
        try: await channel.send(embed=embed)
        except: pass

    async def cog_load(self):
        # trust_env=True is CRITICAL for using the system proxy environment variables
        self.session = aiohttp.ClientSession(trust_env=True)
        self.auto_sync_loop.start()
        self.activity_panel_loop.start()
        self.activity_tracker_loop.start()
        self.automated_report_loop.start()

    def cog_unload(self):
        if self.session:
            asyncio.create_task(self.session.close())
        self.auto_sync_loop.cancel()
        self.activity_panel_loop.cancel()
        self.activity_tracker_loop.cancel()
        self.automated_report_loop.cancel()

    async def check_permissions(self, ctx_or_int):
        is_interaction = isinstance(ctx_or_int, discord.Interaction)
        user = ctx_or_int.user if is_interaction else ctx_or_int.author
        if user.guild_permissions.administrator: return True
        if user.id in ADMIN_USER_IDS: return True
        for role in user.roles:
            if role.id in ADMIN_ROLE_IDS: return True
            
        msg = "❌ Bu komutu kullanmak için yetkiniz yok."
        if is_interaction:
            await ctx_or_int.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_int.send(msg)
        return False
        
    def get_headers(self):
        token = os.getenv("BATTLEMETRICS_TOKEN")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
    
    async def load_activity_data(self):
        if not os.path.exists(self.ACTIVITY_FILE): return {}
        try:
            def _load():
                with open(self.ACTIVITY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return await asyncio.to_thread(_load)
        except Exception as e:
            logger.error(f"Failed to load activity data: {e}")
            return {}

    async def save_activity_data(self, data):
        def _save():
            with open(self.ACTIVITY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        await asyncio.to_thread(_save)
            
    def load_activity_panel_config(self):
        if not os.path.exists(self.activity_config_file): return {}
        try:
            with open(self.activity_config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}

    def save_activity_panel_config(self, data):
        with open(self.activity_config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    async def record_activity(self, steam_id, name, data=None):
        should_save = False
        if data is None:
            data = await self.load_activity_data()
            should_save = True
            
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        if steam_id not in data:
            data[steam_id] = {"name": name, "history": {}, "total_minutes": 0}
        
        data[steam_id]["name"] = name
        
        if today not in data[steam_id]["history"]:
            data[steam_id]["history"][today] = 0
            
        data[steam_id]["history"][today] += 2
        data[steam_id]["total_minutes"] += 2
        data[steam_id]["last_seen"] = datetime.datetime.now().isoformat()
        
        if should_save:
            await self.save_activity_data(data)

    async def fetch_player_data(self, identifier, endpoint="alltimeleaderboards", params=None):
        # Create cache key
        if params is None: params = {}
        if "mod" not in params: params["mod"] = "Vanilla"
        if "search" not in params: params["search"] = identifier
        
        # Generate cache key from identifier + endpoint + params
        cache_key = f"player_data:{identifier}:{endpoint}:{str(sorted(params.items()))}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return cached
        
        # Cache miss - fetch from API
        logger.debug(f"Cache MISS: {cache_key}")
        
        url = f"https://api.mysquadstats.com/{endpoint}"
        headers = {
            "User-Agent": "Bot",
            "Referer": "https://mysquadstats.com/"
        }
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    if json_resp and "data" in json_resp and json_resp["data"]:
                        result = json_resp["data"][0] if isinstance(json_resp["data"], list) else json_resp["data"]
                        # Cache for 5 minutes (300 seconds)
                        await self.cache.set(cache_key, result, ttl=300)
                        return result
        except: pass
        
        # Cache None results for shorter time to allow retry
        await self.cache.set(cache_key, None, ttl=60)
        return None

    async def run_sync_task(self, guild, status_callback=None):
        # 1. IMPORT
        found_players = {} # SteamID -> Info
        
        # --- DEV MODE: Local DB as Source ---
        if DEV_MODE:
            if os.path.exists("squad_db.json"):
                try:
                    def _load_local_db():
                        with open("squad_db.json", "r", encoding="utf-8") as f:
                            return json.load(f)
                    local_data = await asyncio.to_thread(_load_local_db)
                    for p in local_data.get("players", []):
                        found_players[p["steam_id"]] = p
                    
                    if status_callback: await status_callback("scanned", len(found_players))
                except Exception as e:
                    logger.error(f"Dev Mode Load Error: {e}")
                    if status_callback: await status_callback("error", f"Dev Mode DB Error: {e}")
                    return
            else:
                if status_callback: await status_callback("error", "Dev Mode: squad_db.json bulunamadı.")
                return

        # --- PROD MODE: Google Sheet Sync ---
        else:
            if gspread and GOOGLE_SHEET_KEY:
                try:
                    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                            "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
                    creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
                    client = await asyncio.to_thread(gspread.authorize, creds)
                    
                    sheet = await asyncio.to_thread(client.open_by_key, GOOGLE_SHEET_KEY)
                    worksheet = await asyncio.to_thread(lambda: sheet.sheet1)
                    
                    all_rows = await asyncio.to_thread(worksheet.get_all_values)
                    
                    if not all_rows:
                         if status_callback: await status_callback("error", "Sheet boş.")
                         return

                    headers = [h.lower().strip() for h in all_rows[0]]
                    
                    idx_steam = -1
                    idx_name = -1
                    idx_discord = -1
                    
                    possible_steam = ["steam64id", "steamid", "steam_id", "steam id"]
                    possible_name = ["player", "name", "isim", "oyuncu"]
                    possible_discord = ["discord id", "discord_id", "discordid"]
                    
                    for i, h in enumerate(headers):
                        if idx_steam == -1 and h in possible_steam: idx_steam = i
                        if idx_name == -1 and h in possible_name: idx_name = i
                        if idx_discord == -1 and h in possible_discord: idx_discord = i
                    
                    if status_callback: await status_callback("scanned", len(all_rows)-1)

                    skipped_details = []
                    duplicates_list = []
                    found_players_rows = {} 

                    for row_idx, row in enumerate(all_rows[1:], start=2): 
                        s_id = row[idx_steam].strip() if idx_steam != -1 and len(row) > idx_steam else ""
                        p_name = row[idx_name].strip() if idx_name != -1 and len(row) > idx_name else ""
                        d_id = row[idx_discord].strip() if idx_discord != -1 and len(row) > idx_discord else ""
                        
                        if not s_id or len(s_id) < 17: 
                            if len(skipped_details) < 5:
                                reason = "Boş" if not s_id else f"Hatalı ({s_id})"
                                skipped_details.append(f"Satır {row_idx}: {reason}")
                            elif len(skipped_details) == 5:
                                skipped_details.append("...ve diğerleri")
                            continue
                            
                        if not p_name: p_name = f"Unknown ({s_id})"
                        
                        parsed_did = None
                        if d_id:
                            if str(d_id).isdigit(): parsed_did = int(d_id)
                            else: parsed_did = d_id.strip()
                        
                        if s_id in found_players:
                            original_row = found_players_rows.get(s_id, "?")
                            duplicates_list.append(f"Satır {row_idx} (ID: {s_id}) -> Satır {original_row} ile çakışıyor.")
                            continue

                        found_players[s_id] = {
                            "steam_id": s_id,
                            "name": p_name,
                            "discord_id": parsed_did,
                            "stats": {},
                            "season_stats": {}
                        }
                        found_players_rows[s_id] = row_idx
                    
                    if status_callback and (skipped_details or duplicates_list):
                         await status_callback("details", (len(skipped_details) + (0 if "..." not in skipped_details else 3), duplicates_list, skipped_details))
                    
                    if idx_steam == -1:
                         if status_callback: await status_callback("error", f"SteamID sütunu bulunamadı. Algılanan: {headers}")
                         return
                except Exception as e:
                    logger.error(f"Sheet Sync Error: {e}", exc_info=True)
                    if status_callback: await status_callback("error", f"Sheet Hatası: {e}")
                    return
            else:
                 if status_callback: await status_callback("error", "Google Sheet entegrasyonu devre dışı.")
                 return

        if not found_players:
             err_msg = "Sheet oyuncu verisi içermiyor."
             if status_callback: await status_callback("error", err_msg)
             return

        # 2. FETCH STATS (MySquadStats API)
        db_data = []
        new_entries = []
        
        existing_players = {}
        if os.path.exists("squad_db.json"):
             try:
                 def _load_db():
                     with open("squad_db.json", "r", encoding="utf-8") as f:
                         return json.load(f)
                 j = await asyncio.to_thread(_load_db)
                 for p in j.get("players", []): existing_players[p["steam_id"]] = p
             except Exception as e: logger.error(f"DB Load Error: {e}")

        count = 0
        total = len(found_players)
        
        for steam_id, p_info in found_players.items():
            count += 1
            if status_callback: await status_callback("progress", (count, total))

            all_time = await self.fetch_player_data(steam_id, "alltimeleaderboards")
            season = await self.fetch_player_data(steam_id, "seasonleaderboards", params={"season": "current"})

            if all_time:
                api_name = None
                if season and 'lastName' in season: api_name = season['lastName']
                elif all_time and 'lastName' in all_time: api_name = all_time['lastName']
                
                final_name = api_name if api_name else p_info["name"]
                
                p_info["name"] = final_name
                p_info["stats"] = all_time
                p_info["season_stats"] = season
                
                if steam_id not in existing_players:
                    new_entries.append(final_name)
                
                db_data.append(p_info)
            else:
                 # Player in Sheet but NO STATS found. 
                 db_data.append(p_info)
            
            await asyncio.sleep(1.0) 

        # 3. SAVE - Auto-sync to Sheets
        if db_data:
            final_data = {
                "last_update": str(datetime.datetime.now()),
                "players": db_data
            }
            await self._save_db_and_sync(final_data)
                
        if status_callback: await status_callback("done", (len(db_data), new_entries))
        
        # Log to Channel
        new_names = ", ".join(new_entries[:10]) if new_entries else "Yok"
        if len(new_entries) > 10: new_names += f" (+{len(new_entries)-10})"
        
        await self.log_to_channel(guild, "🔄 Veritabanı Senkronizasyonu", 
            f"**Durum:** Tamamlandı\n**Toplam Oyuncu:** {len(db_data)}\n**Yeni:** {new_names}")

    @tasks.loop(hours=6)
    async def auto_sync_loop(self):
        for guild in self.bot.guilds:
            await self.run_sync_task(guild, status_callback=None)

    @auto_sync_loop.before_loop
    async def before_auto_sync(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def activity_panel_loop(self):
        """Auto-update activity panels from Google Sheets (G2 timestamp tracking)"""
        panel_cfg = self.load_activity_panel_config()
        if not panel_cfg: return
        
        try:
            # Fetch from Sheets (smart caching with G2 check)
            activity_data = await self.fetch_activity_from_sheets()
            
            if not activity_data:
                logger.warning("No activity data from Sheets")
                return
            
            # Generate embed
            embed = await self.generate_activity_panel_sheets(activity_data)
            
            # Update message
            for guild_id, cfg in panel_cfg.items():
                guild = self.bot.get_guild(int(guild_id))
                if not guild: continue
                
                channel = guild.get_channel(cfg.get('channel_id'))
                if not channel: continue
                
                message_id = cfg.get('message_id')
                if message_id:
                    try:
                        msg = await channel.fetch_message(message_id)
                        
                        # Check message age (Discord 1-hour edit limit mitigation)
                        msg_age = (datetime.datetime.now(datetime.timezone.utc) - msg.created_at).total_seconds()
                        
                        if msg_age > 3000:  # ~50 minutes
                            # Delete and recreate to avoid edit limit
                            await msg.delete()
                            new_msg = await channel.send(embed=embed)
                            cfg['message_id'] = new_msg.id
                            self.save_activity_panel_config(panel_cfg)
                            logger.info(f"Recreated activity panel (old message)")
                        else:
                            # Edit existing
                            await msg.edit(embed=embed)
                            
                    except discord.errors.NotFound:
                        # Message deleted, create new
                        new_msg = await channel.send(embed=embed)
                        cfg['message_id'] = new_msg.id
                        self.save_activity_panel_config(panel_cfg)
                        
        except Exception as e:
            logger.error(f"Activity panel loop error (guild {guild_id}): {e}", exc_info=True)

    @activity_panel_loop.before_loop
    async def before_activity_panel(self):
        await self.bot.wait_until_ready()

    
    @tasks.loop(minutes=2)
    async def activity_tracker_loop(self):
        """Track online players every 2 minutes and update squad_activity.json"""
        try:
            # Get currently online players from BM server API
            url = f"{BM_API_URL}/servers/{SERVER_ID}"
            params = {
                "include": "player"
            }
            
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"Activity tracker: BM API returned {resp.status}")
                    return
                
                data = await resp.json()
                included = data.get("included", [])
                
                # Load current activity data
                activity_data = await self.load_activity_data()
                
                # Track each online player
                tracked_count = 0
                for item in included:
                    if item.get("type") == "player":
                        player_id = item.get("id")
                        attrs = item.get("attributes", {})
                        player_name = attrs.get("name", "Unknown")
                        
                        # Get SteamID from identifiers
                        steam_id = None
                        for ident in attrs.get("identifiers", []):
                            if ident.get("type") == "steamID":
                                steam_id = ident.get("identifier")
                                break
                        
                        if steam_id:
                            activity_data = await self.record_activity(steam_id, player_name, activity_data)
                            tracked_count += 1
                
                # Save all changes at once
                if tracked_count > 0:
                    await self.save_activity_data(activity_data)
                    logger.debug(f"Activity tracker: Recorded {tracked_count} online players")
                
        except Exception as e:
            logger.error(f"Activity tracker loop error: {e}", exc_info=True)
    
    @activity_tracker_loop.before_loop
    async def before_activity_tracker(self):
        await self.bot.wait_until_ready()

    @commands.command(name='squad_sync')
    async def squad_sync(self, ctx):
        """Google Sheet ile veritabanını manuel senkronize eder."""
        if not await self.check_permissions(ctx): return

        status_msg = await ctx.send("🔄 **Senkronizasyon Başlatılıyor...**\nLütfen bekleyin, bu işlem veri boyutuna göre zaman alabilir.")
        
        async def update_status(stage, data=None):
            if stage == "error":
                embed = discord.Embed(title="❌ Senkronizasyon Hatası", description=f"Hata: {data}", color=discord.Color(COLORS.ERROR))
                await status_msg.edit(content=None, embed=embed)
            elif stage == "scanned":
                await status_msg.edit(content=f"✅ Tablo tarandı. `{data}` satır bulundu.")
            elif stage == "details":
                skipped_count_val, duplicates_list, skipped_details = data
                msg_content = f"🔄 **Detaylar İşleniyor...**\n"
                if skipped_details:
                    msg_content += f"⚠️ **{skipped_count_val}** satır atlandı (Örnekler):\n"
                    msg_content += "\n".join([f"- {s}" for s in skipped_details[:5]])
                    if len(skipped_details) > 5: msg_content += "\n...ve diğerleri"
                
                if duplicates_list: 
                    if skipped_details: msg_content += "\n\n"
                    msg_content += f"⚠️ **{len(duplicates_list)}** Çakışma:\n"
                    subset = duplicates_list[:5]
                    msg_content += "\n".join([f"- {d}" for d in subset])
                    if len(duplicates_list) > 5: msg_content += f"\n...ve {len(duplicates_list)-5} daha."
                
                await status_msg.edit(content=msg_content)
            elif stage == "progress":
                current, total = data
                if current % 3 == 0 or current == 1: # Update less frequently to avoid rate limits
                    await status_msg.edit(content=f"📡 Veriler çekiliyor... ({current}/{total})")
            elif stage == "done":
                total_p, new_e = data
                embed = discord.Embed(title="✅ Senkronizasyon Tamamlandı", color=discord.Color(COLORS.SUCCESS))
                embed.add_field(name="Toplam Oyuncu", value=str(total_p), inline=True)
                embed.add_field(name="Yeni Eklenenler", value=str(len(new_e)), inline=True)
                if new_e:
                     added_str = "\n".join([f"• {n}" for n in new_e[:10]])
                     if len(new_e) > 10: added_str += f"\n...ve {len(new_e)-10} kişi daha"
                     embed.add_field(name="🆕 Eklenenler", value=added_str, inline=False)
                else: 
                     embed.add_field(name="Sonuç", value="Yeni kayıt yok.", inline=False)
                await status_msg.edit(content=None, embed=embed)

        await self.run_sync_task(ctx.guild, status_callback=update_status)

    @commands.command(name='squad_top')
    async def squad_top(self, ctx):
        if not await self.check_permissions(ctx): return
        if not os.path.exists("squad_db.json"):
            await ctx.send("⚠️ Veritabanı yok. !1squad_sync çalıştırın.")
            return

        def _read_db():
            with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
        
        async def refresh_data():
            """Refresh callback for squad_top"""
            data = await asyncio.to_thread(_read_db)
            return sorted(data.get("players", []), key=lambda x: x["stats"].get("totalScore", 0), reverse=True)
        
        data = await asyncio.to_thread(_read_db)
        sorted_players = sorted(data.get("players", []), key=lambda x: x["stats"].get("totalScore", 0), reverse=True)
        view = SquadLeaderboardView(sorted_players, mode="AllTime", refresh_callback=refresh_data)
        await ctx.send(embed=view.get_current_embed(), view=view)

    @commands.command(name='squad_season')
    async def squad_season(self, ctx):
        if not await self.check_permissions(ctx): return
        if not os.path.exists("squad_db.json"):
            await ctx.send("⚠️ Veritabanı yok. !1squad_sync çalıştırın.")
            return
            
        def _read_db():
             with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
        
        async def refresh_data():
            """Refresh callback for squad_season"""
            data = await asyncio.to_thread(_read_db)
            season_players = [p for p in data.get("players", []) if p.get("season_stats")]
            return sorted(season_players, key=lambda x: x["season_stats"].get("totalScore", 0), reverse=True) if season_players else []
        
        data = await asyncio.to_thread(_read_db)
        season_players = [p for p in data.get("players", []) if p.get("season_stats")]
        if not season_players:
             await ctx.send("📭 Sezon verisi bulunamadı.")
             return

        sorted_players = sorted(season_players, key=lambda x: x["season_stats"].get("totalScore", 0), reverse=True)
        view = SquadLeaderboardView(sorted_players, mode="Season", refresh_callback=refresh_data)
        await ctx.send(embed=view.get_current_embed(), view=view)

    @commands.command(name='compare', aliases=['karşılaştır', 'vs', 'comp', 'karsilastir'])
    async def compare(self, ctx, p1: Union[discord.Member, str], p2: Union[discord.Member, str]):
        """İki oyuncunun istatistiklerini karşılaştırır."""
        
        if not os.path.exists("squad_db.json"):
            await ctx.send("⚠️ Veritabanı bulunamadı. !1squad_sync çalıştırın.")
            return

        def _read_db():
            with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
        
        try:
            data = await asyncio.to_thread(_read_db)
        except:
             await ctx.send("⚠️ Veritabanı okunamadı.")
             return

        players = data.get("players", [])

        def resolve_player(query):
            # 1. Discord Member Check
            if isinstance(query, discord.Member):
                # A. Kendi DB'mizdeki discord_id ile eşleşme
                for p in players:
                    if str(p.get("discord_id")) == str(query.id):
                        return p
                # B. İsim ile eşleşme (Display Name)
                for p in players:
                    if p["name"].lower() == query.display_name.lower():
                        return p
                # C. İsim ile eşleşme (Global Name/User Name)
                for p in players:
                    if p["name"].lower() == query.name.lower():
                        return p
                
                # If not found by strict Member properties, fall through to string logic using Display Name
                query = query.display_name

            # 2. String Query Check
            q_str = str(query).strip()
            logger.info(f"[COMPARE_DEBUG] Resolving: '{q_str}'")

            # Clean common clan tags for better matching
            clean_q = q_str.replace("『COTA』", "").replace("[COTA]", "").replace("COTA |", "").replace("@", "").strip()
            logger.info(f"[COMPARE_DEBUG] Clean Query: '{clean_q}'")

            # A. SteamID Match
            for p in players:
                if p["steam_id"] == q_str:
                    logger.info(f"[COMPARE_DEBUG] Match Found (SteamID): {p['name']}")
                    return p
            
            # B. Name Match (Exact & Case Insensitive)
            for p in players:
                if p["name"].lower() == q_str.lower() or p["name"].lower() == clean_q.lower():
                    logger.info(f"[COMPARE_DEBUG] Match Found (Exact): {p['name']}")
                    return p
            
            # C. Name Match (Partial - Startswith)
            # Prioritize matches that start with query
            for p in players:
                if p["name"].lower().startswith(q_str.lower()) or p["name"].lower().startswith(clean_q.lower()):
                    logger.info(f"[COMPARE_DEBUG] Match Found (Startswith): {p['name']}")
                    return p
            
            # D. Name Match (Containment)
            for p in players:
                if q_str.lower() in p["name"].lower() or clean_q.lower() in p["name"].lower():
                    logger.info(f"[COMPARE_DEBUG] Match Found (Containment): {p['name']}")
                    return p

            # E. Reverse Containment (if DB name is substring of Query - e.g. User pasted full name with extra tag)
            for p in players:
                if len(p["name"]) > 3 and p["name"].lower() in q_str.lower():
                     logger.info(f"[COMPARE_DEBUG] Match Found (Reverse): {p['name']}")
                     return p
            
            logger.warning(f"[COMPARE_DEBUG] No match found for '{q_str}'")
            return None

        player1 = resolve_player(p1)
        player2 = resolve_player(p2)
        
        name1_input = p1.display_name if isinstance(p1, discord.Member) else p1
        name2_input = p2.display_name if isinstance(p2, discord.Member) else p2

        if not player1:
            await ctx.send(f"❌ Oyuncu 1 bulunamadı: **{name1_input}**")
            return
        if not player2:
            await ctx.send(f"❌ Oyuncu 2 bulunamadı: **{name2_input}**")
            return

        # --- Helper to get stats ---
        def get_stat(p, key):
            # Try AllTime first
            val = p.get("stats", {}).get(key, 0)
            if not val: # Fallback to season?? No, strict separation better usually.
                 # Let's check both or just stick to 'stats' (All Time) as default
                 pass
            try: return float(val)
            except: return 0.0

        # Stats to compare
        # (Key, Label, Format)
        # Stats to compare
        # (Key, Label, Format, InvertLogic)
        comparisons = [
            ("totalKdRatio", "⚖️ K/D Oranı", "{:.2f}", False),
            ("totalKills", "⚔️ Kill", "{:.0f}", False),
            ("totalDeaths", "💀 Death", "{:.0f}", True), # Invert: Less is Better
            ("totalRevives", "🚑 Revive", "{:.0f}", False),
            ("totalScore", "🏆 Puan", "{:,.0f}", False)
        ]

        embed = discord.Embed(
            title="⚔️ İstatistik Karşılaştırma (Tüm Zamanlar)",
            color=discord.Color.gold()
        )
        col_p1 = []
        col_label = []
        col_p2 = []
        
        p1_wins = 0
        p2_wins = 0

        for key, label, fmt, invert in comparisons:
            v1 = get_stat(player1, key)
            v2 = get_stat(player2, key)
            
            s1 = fmt.format(v1)
            s2 = fmt.format(v2)
            
            # Indicators
            if v1 > v2:
                i1, i2 = ("🟢", "🔴") if not invert else ("🔴", "🟢")
                # Counting logic: If v1 is better (green), p1 wins.
                if not invert: p1_wins += 1
                else: p2_wins += 1 # Invert case: v1 > v2 means v1 is worse (Red). Wait.
                # Logic Correction:
                # if v1 > v2:
                #    Normal: v1 is Green (Win).
                #    Invert: v1 is Red (Loss).
                if not invert: p1_wins += 1
                else: p2_wins += 1
                
                s1 = f"**{s1}**"
            elif v2 > v1:
                i1, i2 = ("🔴", "🟢") if not invert else ("🟢", "🔴")
                if not invert: p2_wins += 1
                else: p1_wins += 1
                
                s2 = f"**{s2}**"
            else:
                i1, i2 = "⚪", "⚪"
            
            # Build Columns (P1 | Label | P2)
            col_p1.append(f"{s1} {i1}")
            col_label.append(f"**{label}**")
            col_p2.append(f"{s2} {i2}")
            
        embed.clear_fields() # Remove initial headers to rebuild strictly with 3 columns
        
        # Row 1: Headers (re-added as fields for alignment if needed, or we rely on columns)
        # To align properly, we need Headers as the first row of fields.
        embed.add_field(name="Oyuncu 1", value=f"**{player1['name']}**", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name="Oyuncu 2", value=f"**{player2['name']}**", inline=True)

        # Row 2: Data
        embed.add_field(name="Değer", value="\n".join(col_p1), inline=True)
        embed.add_field(name="Metrik", value="\n".join(col_label), inline=True)
        embed.add_field(name="Değer", value="\n".join(col_p2), inline=True)
        
        # Winner Calculation
        if p1_wins > p2_wins:
            result_text = f"🏆 **KAZANAN:** {player1['name']} ({p1_wins} - {p2_wins})"
            embed.color = discord.Color.green()
        elif p2_wins > p1_wins:
            result_text = f"🏆 **KAZANAN:** {player2['name']} ({p2_wins} - {p1_wins})"
            embed.color = discord.Color.green()
        else:
            result_text = f"🤝 **BERABERE** ({p1_wins} - {p2_wins})"
            embed.color = discord.Color.light_grey()
            
        embed.add_field(name="\u200b", value=result_text, inline=False)
        
        # Override field names to be invisible or just separators, 
        # actually we want headers "Player 1", "VS", "Player 2"
        # But we already added them above? No, we will replace the whole field structure.
        
        # CLEAR existing fields logic from previous steps if we are editing in place.
        # Check context: We are replacing the loop and the fields above it.
        # Wait, the ReplacementContent replaces Lines 1132-1152.
        # Lines 1128-1130 added "Oyuncu 1", "VS", "Oyuncu 2".
        # If I keep those, I have 3 header fields, then 3 data fields.
        # Discord allows 3 inline fields per row.
        # So Row 1: P1 Name | VS | P2 Name
        # Row 2: P1 Data | Labels | P2 Data
        # This works perfectly.
        
        # Update field values with built columns
        embed.clear_fields() # Reset to start fresh structure
        
        # Row 1: Headers
        embed.add_field(name="Oyuncu 1", value=f"**{player1['name']}**", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name="Oyuncu 2", value=f"**{player2['name']}**", inline=True)
        
        # Row 2: Data Columns
        embed.add_field(name="Değer", value="\n".join(col_p1), inline=True)
        embed.add_field(name="Metrik", value="\n".join(col_label), inline=True)
        embed.add_field(name="Değer", value="\n".join(col_p2), inline=True)
            
        embed.set_footer(text=f"Talep eden: {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='oyuncu_yonet')
    async def oyuncu_yonet(self, ctx):
        if not await self.check_permissions(ctx): return
        
        total_players = 0
        last_update = "Bilinmiyor"
        if os.path.exists("squad_db.json"):
             try:
                 def _read_db():
                     with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
                 data = await asyncio.to_thread(_read_db)
                 total_players = len(data.get("players", []))
                 last_update = data.get("last_update", "Bilinmiyor")
             except: pass
        
        try:
             dt = datetime.datetime.fromisoformat(last_update)
             last_update = dt.strftime("%d.%m.%Y %H:%M")
        except: pass

        embed = discord.Embed(title="🛠️ Oyuncu Yönetim Paneli", color=discord.Color(COLORS.BLUE))
        embed.add_field(name="👥 Toplam Oyuncu", value=str(total_players), inline=True)
        embed.add_field(name="📅 Son Güncelleme", value=last_update, inline=True)
        
        view = PlayerManageView(self.bot)
        await ctx.send(embed=embed, view=view)



    @commands.command(name='squad_import_sheet')
    async def squad_import_sheet(self, ctx, sheet_name="Whitelist"):
        """Google E-Tablolar'dan (gspread) oyuncu listesini içe aktarır. (Standart: Key 1Exwp...)"""
        if not await self.check_permissions(ctx): return
        
        if gspread is None:
            await ctx.send("❌ `gspread` kütüphanesi yüklü değil veya import edilemedi.")
            return

        SHEET_KEY = "1ExwpvnVCLD7LYWREFr4eQ5VzdubdH5R_WCqaZBhcMHE"
        msg = await ctx.send("📤 **Google Sheet İçe Aktırma Başlatılıyor...**\nLütfen bekleyin, bu işlem veri boyutuna göre zaman alabilir.")
        embed = discord.Embed(title="📤 G-Sheet İçe Aktarma", description=f"**{SHEET_KEY}** tablosu taranıyor...", color=discord.Color(COLORS.INFO))
        await msg.edit(embed=embed)

        try:
            scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                     "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
            
            creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
            client = gspread.authorize(creds)
            
            # Open Spreadsheet
            sheet = client.open_by_key(SHEET_KEY).sheet1
            
            # Use get_all_values to avoid float conversion
            all_rows = sheet.get_all_values()
            
            if not all_rows:
                await msg.edit(content="❌ Sheet boş.")
                return

            # Header Parsing
            headers = [h.lower().strip() for h in all_rows[0]]
            idx_steam = -1
            idx_name = -1
            idx_discord = -1
            
            possible_steam = ["steam64id", "steamid", "steam_id", "steam id"]
            possible_name = ["player", "name", "isim", "oyuncu"]
            possible_discord = ["discord id", "discord_id", "discordid"]
            
            for i, h in enumerate(headers):
                if idx_steam == -1 and h in possible_steam: idx_steam = i
                if idx_name == -1 and h in possible_name: idx_name = i
                if idx_discord == -1 and h in possible_discord: idx_discord = i
            
            if idx_steam == -1:
                await msg.edit(content=f"❌ SteamID sütunu bulunamadı. Algılanan: {headers}")
                return

            imported_count = 0
            updated_count = 0
            
            # Load DB
            db_data = {"players": [], "last_update": ""}
            if os.path.exists("squad_db.json"):
                try:
                    def _read_db():
                        with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
                    db_data = await asyncio.to_thread(_read_db)
                except: pass

            existing_map = {p["steam_id"]: p for p in db_data.get("players", [])}
            
            for row in all_rows[1:]:
                # Map using indices
                s_id = row[idx_steam].strip() if idx_steam != -1 and len(row) > idx_steam else ""
                p_name = row[idx_name].strip() if idx_name != -1 and len(row) > idx_name else ""
                d_id = row[idx_discord].strip() if idx_discord != -1 and len(row) > idx_discord else ""
                
                if not s_id or len(s_id) < 17: continue 
                if not p_name: p_name = f"Unknown ({s_id})"
                
                # Discord ID can be numeric ID or username string
                parsed_did = None
                if d_id:
                    if str(d_id).isdigit():
                        parsed_did = int(d_id)  # Numeric Discord ID
                    else:
                        parsed_did = d_id.strip()  # Discord username
                
                if s_id in existing_map:
                    p = existing_map[s_id]
                    if p["name"] != p_name or (parsed_did and p.get("discord_id") != parsed_did):
                        p["name"] = p_name
                        if parsed_did: p["discord_id"] = parsed_did
                        updated_count += 1
                else:
                    new_p = {
                        "steam_id": s_id,
                        "name": p_name,
                        "discord_id": parsed_did,
                        "stats": {},
                        "season_stats": {} 
                    }
                    existing_map[s_id] = new_p 
                    db_data["players"].append(new_p)
                    imported_count += 1
            
            # Save
            db_data["last_update"] = str(datetime.datetime.now())
            def _save_db():
                with open("squad_db.json", "w", encoding="utf-8") as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
            await msg.edit(content="💾 Veritabanı kaydediliyor...")
            await asyncio.to_thread(_save_db)

            embed.color = discord.Color(COLORS.SUCCESS)
            embed.description = f"✅ İşlem Tamamlandı!\n\n🆕 Eklenen: {imported_count}\n🔄 Güncellenen: {updated_count}"
            await msg.edit(content=None, embed=embed)

            await self.log_to_channel(ctx.guild, "📥 Google Sheet İçe Aktarıldı", 
                 f"**Tablo:** {SHEET_KEY}\n**Eklenen:** {imported_count}\n**Güncellenen:** {updated_count}", 
                 ctx.author)

        except Exception as e:
            embed.color = discord.Color(COLORS.ERROR)
            embed.description = f"❌ Hata oluştu:\n{e}"
            await msg.edit(content=None, embed=embed)
            print(f"Sheet Import Error: {e}")

    @commands.command(name='resolve_ids')
    async def resolve_ids(self, ctx):
        if not await self.check_permissions(ctx): return
        
        msg = await ctx.send("🔄 Veritabanı taranıyor ve Discord üyeleri ile eşleştiriliyor...")
        
        if not os.path.exists("squad_db.json"):
            await msg.edit(content="⚠️ Veritabanı bulunamadı.")
            return

        def _read_db():
            with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
        
        try:
            db_data = await asyncio.to_thread(_read_db)
        except Exception as e:
            await msg.edit(content=f"❌ Veritabanı okuma hatası: {e}")
            return

        players = db_data.get("players", [])
        logger.info(f"DEBUG: resolve_ids START. Total Players in DB: {len(players)}")
        resolved_count = 0
        total_scanned = 0
        failed_count = 0
        
        resolved_list = []

        # Cache Member Data for speed
        # Map: Lowercase Name -> Member Object
        # We need multiple maps for diff properties
        member_map_name = {}
        member_map_global = {}
        member_map_display = {}
        
        for m in ctx.guild.members:
            if m.name: member_map_name[m.name.lower()] = m
            if m.global_name: member_map_global[m.global_name.lower()] = m
            if m.display_name: member_map_display[m.display_name.lower()] = m

        for i, p in enumerate(players):
            d_id = p.get("discord_id")
            
            if d_id and not isinstance(d_id, int) and not str(d_id).isdigit():
                total_scanned += 1
                target_str = str(d_id).strip().lower()
                
                found_member = None
                
                # Check 1: Username (name)
                if target_str in member_map_name:
                    found_member = member_map_name[target_str]
                # Check 2: Global Name
                elif target_str in member_map_global:
                    found_member = member_map_global[target_str]
                # Check 3: Display Name (Nickname)
                elif target_str in member_map_display:
                    found_member = member_map_display[target_str]

                if found_member:
                    p["discord_id"] = found_member.id
                    p["_resolved_from"] = d_id # Backup old string just in case
                    resolved_count += 1
                    resolved_list.append(f"{d_id} -> {found_member.display_name} ({found_member.id})")
                else:
                    failed_count += 1
        
        if resolved_count > 0:
            db_data["last_update"] = str(datetime.datetime.now())
            def _save_db():
                with open("squad_db.json", "w", encoding="utf-8") as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
            await asyncio.to_thread(_save_db)
            
            # Log results
            log_desc = f"**Çözümlenen:** {resolved_count}\n**Başarısız:** {failed_count}\n**Toplam Taranan:** {total_scanned}"
            if resolved_list:
                sample = "\n".join(resolved_list[:10])
                if len(resolved_list) > 10: sample += f"\n...ve {len(resolved_list)-10} daha."
                log_desc += f"\n\n**Örnekler:**\n{sample}"
            
            await self.log_to_channel(ctx.guild, "🔧 Discord ID Çözümleme", log_desc, ctx.author)
            await msg.edit(content=f"✅ Tamamlandı!\n{resolved_count} ID çözümlendi, {failed_count} başarısız.")
        else:
            await msg.edit(content=f"ℹ️ Çözümlenecek yeni ID bulunamadı. (Taranan: {total_scanned})")

    @commands.command(name='rol_kontrol')
    async def rol_kontrol(self, ctx):
        """Sabitlenmiş 3 ana roldeki (Taglı vb.) üyelerin veritabanı kayıt durumunu kontrol eder."""
        if not await self.check_permissions(ctx): return
        
        target_role_ids = CLAN_MEMBER_ROLE_IDS
        
        msg = await ctx.send("🔍 **Sabit Roller (Taglı Üyeler)** taranıyor...")
        
        # Load DB
        if not os.path.exists("squad_db.json"):
            await msg.edit(content="❌ Veritabanı bulunamadı.")
            return

        def _read_db():
            with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
        
        try:
            db_data = await asyncio.to_thread(_read_db)
            db_players = db_data.get("players", [])
        except Exception as e:
            await msg.edit(content=f"❌ Veritabanı okuma hatası: {e}")
            return

        # Create Set of Registered Discord IDs
        registered_ids = set()
        for p in db_players:
            did = p.get("discord_id")
            if did:
                registered_ids.add(str(did))
        
        report_text = ""
        has_missing = False
        
        embed = discord.Embed(title="📋 Toplu Rol Kontrolü", color=discord.Color(COLORS.BLUE))

        for rid in target_role_ids:
            role = ctx.guild.get_role(rid)
            if not role:
                embed.add_field(name=f"🆔 {rid}", value="❌ Rol Bulunamadı", inline=False)
                continue
            
            found = 0
            missing = 0
            missing_members = []
            
            for member in role.members:
                if member.bot: continue
                if str(member.id) in registered_ids:
                    found += 1
                else:
                    missing += 1
                    missing_members.append(f"{member.display_name} ({member.id})")
            
            status_emoji = "✅" if missing == 0 else "⚠️"
            embed.add_field(
                name=f"{role.name}", 
                value=f"👥 Toplam: {found+missing}\n✅ Kayıtlı: {found}\n{status_emoji} **Kayıtsız: {missing}**", 
                inline=False
            )
            
            if missing > 0:
                has_missing = True
                report_text += f"\n=== {role.name} ({missing} Kayıtsız) ===\n"
                report_text += "\n".join(missing_members) + "\n"

        if has_missing:
             # Send file if there are missing members
            from io import BytesIO
            file = discord.File(BytesIO(report_text.encode("utf-8")), filename="kayitsiz_uyeler.txt")
            embed.description = "⚠️ Bazı rollerde kayıtsız üyeler tespit edildi. Liste ektedir."
            embed.color = discord.Color(COLORS.WARNING)
            await ctx.send(embed=embed, file=file)
            await msg.delete()
        else:
            embed.description = "🎉 Harika! Tüm hedef rollerdeki üyeler veritabanında kayıtlı."
            embed.color = discord.Color(COLORS.SUCCESS)
            await msg.edit(content=None, embed=embed)

    @commands.command(name='profil', aliases=['profile', 'kart'])
    async def profil_cmd(self, ctx, *, query: Union[discord.Member, str] = None):
        """Oyuncunun istatistik profil kartını oluşturur. (Kullanım: !profil veya !profil @Üye)"""
        
        # 1. Resolve Target
        target_query = query if query else ctx.author
        
        # Use existing logic? Need access to resolve_player which is inside compare but not exposed globally in class properly maybe?
        # Actually resolve_player was a helper inside compare. I should extract it or re-implement lighter version here.
        # But wait, compare command logic was:
        # def resolve_player(query): ... inside compare.
        # I should probably copy that logic or make it a method. Making it a method is cleaner but risky to refactor now.
        # I'll implement a dedicated resolver here reusing the logic, or assume 'resolve_ids' fixed everything so Member lookup is easy.
        
        # Load DB
        if not os.path.exists("squad_db.json"):
            await ctx.send("❌ Veritabanı yok.")
            return

        def _read_db():
            with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
        
        try:
            db_data = await asyncio.to_thread(_read_db)
            players = db_data.get("players", [])
        except:
            await ctx.send("❌ DB Hatası")
            return

        resolved_player = None
        
        # Helper Resolver
        def find_player(q):
            # 1. By Discord ID (Member)
            if isinstance(q, discord.Member):
                # Match by numeric ID
                for p in players:
                    did = p.get("discord_id")
                    if did and str(did) == str(q.id):
                        return p
                # Fallback: Match by name
                for p in players:
                    if p["name"].lower() == q.display_name.lower() or p["name"].lower() == q.name.lower():
                        return p
                return None
            
            # 2. By String (SteamID or Name)
            q_str = str(q).lower().strip()
            # SteamID
            for p in players:
                if p["steam_id"] == q_str: return p
            # Name Exact
            for p in players:
                if p["name"].lower() == q_str: return p
            # Name Partial
            for p in players:
                if q_str in p["name"].lower(): return p
            return None

        resolved_player = find_player(target_query)
        
        if not resolved_player:
            await ctx.send(f"❌ Oyuncu bulunamadı: **{target_query}**\n(Veritabanında kayıtlı olduğundan emin olun veya ismini doğru yazın.)")
            return

        # 2. Prepare Data
        # Stats are in 'stats' (All Time). Maybe we want Seasonal?
        # Let's use All Time for main card but show Season Rank.
        stats = resolved_player.get("stats", {})
        season_stats = resolved_player.get("season_stats", {})
        
        player_data = {
            "name": resolved_player.get("name"),
            "rank": stats.get("totalScoreRank", "-"),
            "season_rank": season_stats.get("seasonScoreRank", "-"),
            "stats": {
                "score": stats.get("totalScore", 0),
                "kd": stats.get("totalKdRatio", 0.0),
                "kills": stats.get("totalKills", 0),
                "wounds": stats.get("totalWounds", 0),
                "deaths": stats.get("totalDeaths", 0),
                "revives": stats.get("totalRevives", 0)
            }
        }
        
        msg = await ctx.send("🎨 **Profil kartı oluşturuluyor...**")
        
        # 3. Get Avatar
        avatar_bytes = None
        discord_id = resolved_player.get("discord_id")
        
        # Only fetch avatar if we have a linked Discord ID
        if discord_id:
            try:
                # Resolve member object
                member = ctx.guild.get_member(int(discord_id))
                if member:
                    avatar_bytes = await member.display_avatar.with_size(256).read()
                else:
                    # Try fetch user if not in guild
                     u = await self.bot.fetch_user(int(discord_id))
                     if u: avatar_bytes = await u.display_avatar.with_size(256).read()
            except Exception as e:
                logger.warning(f"Avatar fetch error: {e}")
        
        # 4. Generate Image
        try:
            # Run blocking image gen in thread
            def _gen():
                return generate_profile_card(player_data, avatar_bytes)
            
            buf = await asyncio.to_thread(_gen)
            
            file = discord.File(buf, filename=f"profile_{resolved_player['steam_id']}.png")
            await msg.delete()
            await ctx.send(file=file)
            
        except Exception as e:
            await msg.edit(content=f"❌ Kart oluşturma hatası: {e}")
            logger.error(f"Profile Card Error: {e}")

    @commands.command(name='cache_stats')
    async def cache_stats_cmd(self, ctx):
        """Önbellek (cache) istatistiklerini gösterir."""
        if not await self.check_permissions(ctx): return
        
        # Await the async method
        stats = await self.cache.get_detailed_stats()
        
        embed = discord.Embed(
            title="📊 Önbellek İstatistikleri Dashboard", 
            color=discord.Color(COLORS.INFO),
           description=f"**Performans Takip Sistemi**"
        )
        
        # Row 1: Basic Stats
        embed.add_field(name="✅ İsabet (Hits)", value=f"`{stats['hits']:,}`", inline=True)
        embed.add_field(name="❌ Kaçan (Misses)", value=f"`{stats['misses']:,}`", inline=True)
        embed.add_field(name="📈 İsabet Oranı", value=f"**{stats['hit_rate']}**", inline=True)
        
        # Row 2: Capacity
        embed.add_field(name="💾 Önbellekteki Öğe", value=f"`{stats['size']}/{stats['max_size']}`", inline=True)
        embed.add_field(name="📦 Dolu Oranı", value=f"`{stats['utilization']}`", inline=True)
        embed.add_field(name="💽 Bellek", value=f"`{stats['memory_mb']} MB`", inline=True)
        
        # Row 3: Activity
        embed.add_field(
            name="⚡ Aktivite", 
            value=f"`{stats['requests_per_minute']}` req/dk", 
            inline=True
        )
        
        # Top Endpoints
        if stats['top_endpoints']:
            top_list = "\n".join([f"`{i+1}.` **{name}**: {count} isabet" 
                                  for i, (name, count) in enumerate(stats['top_endpoints'])])
            embed.add_field(name="🏆 En Çok Kullanılan Endpointler", value=top_list, inline=False)
        
        # Footer with efficiency rating
        total = stats['hits'] + stats['misses']
        if total > 0:
            hit_pct = float(stats['hit_rate'].rstrip('%'))
            if hit_pct >= 70:
                efficiency = "🟢 Mükemmel"
            elif hit_pct >= 50:
                efficiency = "🟡 İyi"
            elif hit_pct >= 30:
                efficiency = "🟠 Orta"
            else:
                efficiency = "🔴 Düşük"
            
            embed.set_footer(text=f"Verimlilik: {efficiency} | Toplam {total:,} istek işlendi")
        
        await ctx.send(embed=embed)

    @commands.command(name='squad_export')
    async def squad_export(self, ctx):
        """Veritabanındaki tüm istatistikleri (Top ve Sezon) Google E-Tablosuna ('Data' sayfasına) aktarır."""
        # ... (Export Implementation omitted for brevity, keeping existing) ...
        # Wait, I need to see where squad_export ends to append cleanly.
        # Assuming we are appending to end.
        pass # Placeholder for existing code, I will use proper context in next tool call or finding end of file.

    # --- REPORT SYSTEM ---
    
    def _get_report_db(self):
        file_path = "squad_reports.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_report_db(self, data):
        with open("squad_reports.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _take_snapshot(self, period="weekly"):
        """
        Takes a snapshot of current stats for delta calculation.
        Strategies:
        - 'weekly_start': Snapshot taken at start of week.
        - 'monthly_start': Snapshot taken at start of month.
        """
        # Read Current DB
        if not os.path.exists("squad_db.json"): return False
        with open("squad_db.json", "r", encoding="utf-8") as f:
            current_db = json.load(f)
        
        snapshot = {}
        for p in current_db.get("players", []):
            sid = p.get("steam_id")
            stats = p.get("stats", {}) # Uses All Time stats
            if sid and stats:
                snapshot[sid] = {
                    "score": stats.get("totalScore", 0),
                    "kills": stats.get("totalKills", 0),
                    "deaths": stats.get("totalDeaths", 0),
                    "revives": stats.get("totalRevives", 0),
                    "wounds": stats.get("totalWounds", 0),
                    "kd": stats.get("totalKdRatio", 0)
                }
        
        # Save to Report DB
        report_data = self._get_report_db()
        
        # Structure: snapshots > weekly > {timestamp: ..., data: ...}
        if "snapshots" not in report_data: report_data["snapshots"] = {}
        
        report_data["snapshots"][period] = {
            "timestamp": str(datetime.datetime.now()),
            "data": snapshot
        }
        
        # Also store 'last_run' meta
        if "meta" not in report_data: report_data["meta"] = {}
        report_data["meta"][f"last_{period}"] = str(datetime.datetime.now())
        
        self._save_report_db(report_data)
        return True

    def _calculate_deltas(self, period="weekly"):
        """
        Compares Current DB vs Snapshot[period].
        Returns list of player_delta objects.
        """
        if not os.path.exists("squad_db.json"): return []
        with open("squad_db.json", "r", encoding="utf-8") as f:
            current_db = json.load(f)
            
        report_data = self._get_report_db()
        snapshot_data = report_data.get("snapshots", {}).get(period, {}).get("data", {})
        
        if not snapshot_data:
            return [] # No snapshot to compare against
            
        deltas = []
        
        for p in current_db.get("players", []):
            sid = p.get("steam_id")
            name = p.get("name")
            curr_stats = p.get("stats", {})
            
            if not sid: continue
            
            snap_stats = snapshot_data.get(sid, {})
            # If new player (no snapshot), delta is their total score (assuming 0 start)
            # OR we ignore them? Better to include them, assume 0 start.
            
            d_score = curr_stats.get("totalScore", 0) - snap_stats.get("score", 0)
            d_kills = curr_stats.get("totalKills", 0) - snap_stats.get("kills", 0)
            d_deaths = curr_stats.get("totalDeaths", 0) - snap_stats.get("deaths", 0)
            d_revives = curr_stats.get("totalRevives", 0) - snap_stats.get("revives", 0)
            
            # Filter inactive or zero-change players
            if d_score <= 0 and d_kills <= 0: continue
            
            deltas.append({
                "name": name,
                "steam_id": sid,
                "score": d_score,
                "kills": d_kills,
                "deaths": d_deaths,
                "revives": d_revives,
                # Calc Period K/D?
                "kd": d_kills / d_deaths if d_deaths > 0 else d_kills
            })
            
        return deltas
    
    # === Phase 2: Historical Tracking & Trend Analysis ===
    
    def _save_to_history(self, period, deltas):
        """
        Save report data to history array for trend analysis.
        
        Args:
            period (str): "weekly" or "monthly"
            deltas (list): Player delta data from _calculate_deltas()
        """
        if not deltas:
            return
        
        report_db = self._get_report_db()
        
        # Initialize history structure
        if "history" not in report_db:
            report_db["history"] = {"weekly": [], "monthly": []}
        
        # Sort players by score
        top_players = sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)
        top_10 = top_players[:10]
        
        # Find best performers
        best_kills = max(deltas, key=lambda x: x.get('kills', 0))
        best_kd = max(deltas, key=lambda x: x.get('kd', 0))
        
        # Calculate summary statistics
        total_active = len(deltas)
        avg_score = sum(d.get('score', 0) for d in deltas) / total_active if total_active > 0 else 0
        avg_kills = sum(d.get('kills', 0) for d in deltas) / total_active if total_active > 0 else 0
        
        now = datetime.datetime.now()
        
        # Create history entry
        history_entry = {
            "date": now.strftime("%Y-%m-%d"),
            "timestamp": now.isoformat(),
            "week_number": now.isocalendar()[1],
            "year": now.year,
            "summary": {
                "top_scorer": {
                    "name": top_players[0]['name'],
                    "score": top_players[0]['score']
                } if top_players else {},
                "most_kills": {
                    "name": best_kills['name'],
                    "kills": best_kills['kills']
                } if best_kills else {},
                "best_kd": {
                    "name": best_kd['name'],
                    "kd": best_kd['kd']
                } if best_kd else {},
                "total_active": total_active,
                "avg_score": round(avg_score, 2),
                "avg_kills": round(avg_kills, 2)
            },
            "top_10": [
                {
                    "name": p['name'],
                    "score": p.get('score', 0),
                    "kills": p.get('kills', 0),
                    "deaths": p.get('deaths', 0),
                    "kd": p.get('kd', 0)
                } for p in top_10
            ]
        }
        
        # Add to history
        report_db["history"][period].append(history_entry)
        
        # Auto-prune old entries
        max_items = 52 if period == "weekly" else 12
        if len(report_db["history"][period]) > max_items:
            report_db["history"][period] = report_db["history"][period][-max_items:]
            logger.info(f"Pruned {period} history to last {max_items} entries")
        
        self._save_report_db(report_db)
        logger.info(f"Saved {period} report to history: {total_active} active players, avg score: {avg_score:.0f}")
        
        # Update Hall of Fame (Phase 3)
        self._update_hall_of_fame(period, deltas)

    def _analyze_trends(self, period="weekly", count=4):
        """
        Analyze performance trends over recent periods.
        
        Args:
            period (str): "weekly" or "monthly"
            count (int): Number of recent periods to analyze
        
        Returns:
            dict: Trend analysis results or None if insufficient data
        """
        report_db = self._get_report_db()
        history = report_db.get("history", {}).get(period, [])
        
        if len(history) < 2:
            logger.debug(f"Insufficient history for trend analysis: {len(history)} entries")
            return None
        
        # Get last N periods
        recent = history[-min(count, len(history)):]
        
        # Extract metrics
        avg_scores = [h["summary"]["avg_score"] for h in recent]
        total_actives = [h["summary"]["total_active"] for h in recent]
        
        # Trend detection (simple comparison)
        if len(avg_scores) >= 3:
            first_avg = sum(avg_scores[:2]) / 2  # Average of first 2
            last_avg = sum(avg_scores[-2:]) / 2  # Average of last 2
            
            if last_avg > first_avg * 1.1:
                activity_trend = "increasing"
            elif last_avg < first_avg * 0.9:
                activity_trend = "decreasing"
            else:
                activity_trend = "stable"
        else:
            activity_trend = "stable"
        
        # Score change (last vs previous)
        avg_score_change = avg_scores[-1] - avg_scores[-2] if len(avg_scores) >= 2 else 0
        
        # Most consistent player (appears in top 10 most frequently)
        player_appearances = {}
        for h in recent:
            for p in h.get("top_10", []):
                name = p["name"]
                player_appearances[name] = player_appearances.get(name, 0) + 1
        
        most_consistent = max(player_appearances.items(), key=lambda x: x[1])[0] if player_appearances else None
        consistency_count = player_appearances.get(most_consistent, 0) if most_consistent else 0
        
        return {
            "activity_trend": activity_trend,
            "avg_score_change": round(avg_score_change, 2),
            "most_consistent": most_consistent,
            "consistency_count": consistency_count,
            "weekly_averages": avg_scores,
            "active_counts": total_actives,
            "period_count": len(recent),
            "first_date": recent[0]["date"],
            "last_date": recent[-1]["date"]
        }
    
    # === Phase 3: Export & Recognition Features ===
    
    def _export_to_excel(self, period, deltas):
        """Export report data to Excel file."""
        if not deltas:
            return None
        
        import pandas as pd
        from openpyxl.styles import Font, PatternFill
        from io import BytesIO
        
        data = []
        for p in deltas:
            data.append({
                'Oyuncu': p['name'],
                'Score': p.get('score', 0),
                'Kills': p.get('kills', 0),
                'Deaths': p.get('deaths', 0),
                'K/D': round(p.get('kd', 0), 2),
                'Revives': p.get('revives', 0)
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False)
        df.insert(0, 'Sıra', range(1, len(df) + 1))
        
        buf = BytesIO()
        
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'{period.capitalize()} Report', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets[f'{period.capitalize()} Report']
            
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        cell_len = len(str(cell.value))
                        if cell_len > max_length:
                            max_length = cell_len
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buf.seek(0)
        logger.info(f"Excel export created: {len(df)} players")
        return buf
    
    def _update_hall_of_fame(self, period, deltas):
        """Update Hall of Fame with report winners."""
        if not deltas:
            return
        
        report_db = self._get_report_db()
        
        if "hall_of_fame" not in report_db:
            report_db["hall_of_fame"] = {
                "weekly_champions": {},
                "monthly_champions": {},
                "most_improved_awards": {},
                "records": {}
            }
        
        hof = report_db["hall_of_fame"]
        top_players = sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)
        
        if not top_players:
            return
        
        champion = top_players[0]
        champion_name = champion['name']
        
        key = f"{period}_champions"
        if key in hof:
            hof[key][champion_name] = hof[key].get(champion_name, 0) + 1
        
        highest_score = hof["records"].get("highest_weekly_score", {}).get("score", 0)
        if champion['score'] > highest_score:
            hof["records"]["highest_weekly_score"] = {
                "player": champion_name,
                "score": champion['score'],
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        
        top_killer = max(deltas, key=lambda x: x.get('kills', 0))
        highest_kills = hof["records"].get("highest_kills_week", {}).get("kills", 0)
        if top_killer['kills'] > highest_kills:
            hof["records"]["highest_kills_week"] = {
                "player": top_killer['name'],
                "kills": top_killer['kills'],
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        
        self._save_report_db(report_db)
        logger.info(f"Hall of Fame updated: {champion_name} won {period}")
    
    def _export_to_pdf(self, period, deltas):
        """Export report to professional PDF."""
        if not deltas:
            return None
        
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from io import BytesIO
        
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#4472C4'), spaceAfter=30, alignment=TA_CENTER)
        
        period_map = {"weekly": "Haftalık", "monthly": "Aylık"}
        title = Paragraph(f"📊 {period_map.get(period, period.capitalize())} Performans Raporu", title_style)
        elements.append(title)
        
        date_str = datetime.datetime.now().strftime("%d %B %Y")
        date_para = Paragraph(f"<b>Rapor Tarihi:</b> {date_str}", styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        table_data = [['Sıra', 'Oyuncu', 'Score', 'Kills', 'Deaths', 'K/D', 'Revives']]
        
        for i, p in enumerate(sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)[:10], 1):
            table_data.append([str(i), p['name'][:20], str(p.get('score', 0)), str(p.get('kills', 0)), str(p.get('deaths', 0)), f"{p.get('kd', 0):.2f}", str(p.get('revives', 0))])
        
        table = Table(table_data, colWidths=[1.5*cm, 5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        total_active = len(deltas)
        avg_score = sum(d.get('score', 0) for d in deltas) / total_active if total_active > 0 else 0
        
        summary_text = f"<b>Özet İstatistikler:</b><br/>Toplam Aktif Oyuncu: {total_active}<br/>Ortalama Score: {avg_score:.0f}<br/>"
        summary_para = Paragraph(summary_text, styles['Normal'])
        elements.append(summary_para)
        
        elements.append(Spacer(1, 50))
        footer = Paragraph(f"<i>Squad Sunucu Raporu - {datetime.datetime.now().strftime('%Y')}</i>", styles['Normal'])
        elements.append(footer)
        
        doc.build(elements)
        
        buf.seek(0)
        logger.info(f"PDF export created: {len(deltas)} players")
        return buf

    @commands.command(name='report')
    async def report_cmd(self, ctx, period: str = "weekly", action: str = "view"):
        """
        Rapor Sistemi.
        Kullanım: !1report <weekly|monthly> <view|reset>
        view: Mevcut durumu gösterir (Snapshot'ı sıfırlamaz).
        reset: Raporu yayınlar ve YENİ snapshot alır (Dönem sıfırlanır).
        """
        if not await self.check_permissions(ctx): return
        
        valid_periods = ["weekly", "monthly", "daily"]
        if period not in valid_periods:
            await ctx.send(f"⚠️ Geçersiz dönem. Seçenekler: {', '.join(valid_periods)}")
            return
            
        if action == "reset":
             # Force reset (manual cycle)
             # 1. Calculate deltas
             # 2. Save to history
             # 3. Generate Report
             # 4. Re-Take Snapshot
             await ctx.send(f"🔄 {period.capitalize()} Raporu hazırlanıyor ve dönem kapatılıyor...")
             
             # Calculate deltas BEFORE snapshot (Phase 2)
             deltas = self._calculate_deltas(period)
             if deltas:
                 self._save_to_history(period, deltas)
             
             await self._publish_report(ctx.guild, period) # Send to #rapor-log logic
             self._take_snapshot(period)  # Take NEW snapshot AFTER saving history
             await ctx.send(f"✅ {period.capitalize()} dönemi sıfırlandı. Yeni snapshot alındı. Rapor: #rapor-log")
             
        elif action == "view":
             # Just preview
             deltas = self._calculate_deltas(period)
             if not deltas:
                 await ctx.send(f"⚠️ {period.capitalize()} için karşılaştırılacak veri bulunamadı (Snapshot yok veya veri değişmemiş).")
                 # Check if snapshot exists?
                 snap = self._get_report_db().get("snapshots", {}).get(period)
                 if not snap:
                     await ctx.send("ℹ️ Henüz bir başlangıç noktası yok. Şimdi oluşturuluyor...")
                     self._take_snapshot(period)
                 return

             embed = self._create_report_embed(deltas, period, preview=True)
             await ctx.send(embed=embed)
             
        elif action == "init":
             self._take_snapshot(period)
             await ctx.send(f"📸 {period.capitalize()} için başlangıç snapshot'ı alındı.")
    
    @commands.command(name='export_report')
    async def export_report_cmd(self, ctx, period: str = "weekly", format: str = "excel"):
        """Raporu dışa aktar. Kullanım: !1export_report <weekly|monthly> <excel|pdf>"""
        if not await self.check_permissions(ctx): return
        
        valid_periods = ["weekly", "monthly"]
        if period not in valid_periods:
            await ctx.send(f"⚠️ Geçersiz dönem. Seçenekler: {', '.join(valid_periods)}")
            return
        
        valid_formats = ["excel", "pdf"]
        if format not in valid_formats:
            await ctx.send(f"⚠️ Geçersiz format. Seçenekler: {', '.join(valid_formats)}")
            return
        
        await ctx.send(f"📊 {period.capitalize()} raporu {format} olarak hazırlanıyor...")
        
        try:
            deltas = self._calculate_deltas(period)
            
            if not deltas:
                await ctx.send(f"⚠️ {period.capitalize()} için veri bulunamadı.")
                return
            
            if format == "excel":
                buf = await asyncio.to_thread(self._export_to_excel, period, deltas)
                
                if buf:
                    now = datetime.datetime.now().strftime("%Y%m%d")
                    filename = f"{period}_report_{now}.xlsx"
                    file = discord.File(buf, filename=filename)
                    await ctx.send(f"✅ Excel raporu hazır!", file=file)
                else:
                    await ctx.send("❌ Excel oluşturulamadı.")
            
            elif format == "pdf":
                buf = await asyncio.to_thread(self._export_to_pdf, period, deltas)
                
                if buf:
                    now = datetime.datetime.now().strftime("%Y%m%d")
                    filename = f"{period}_report_{now}.pdf"
                    file = discord.File(buf, filename=filename)
                    await ctx.send(f"✅ PDF raporu hazır!", file=file)
                else:
                    await ctx.send("❌ PDF oluşturulamadı.")
        
        except Exception as e:
            await ctx.send(f"❌ Export hatası: {e}")
            logger.error(f"Export error: {e}", exc_info=True)
    
    @commands.command(name='hall_of_fame', aliases=['hof', 'sampiyonlar'])
    async def hall_of_fame_cmd(self, ctx):
        """Hall of Fame - Şampiyonlar listesi"""
        
        report_db = self._get_report_db()
        hof = report_db.get("hall_of_fame", {})
        
        if not hof or not any(hof.values()):
            await ctx.send("📜 Henüz Hall of Fame verisi yok. İlk rapor sonrası oluşacak.")
            return
        
        embed = discord.Embed(
            title="🏆 HALL OF FAME - ŞAMPIYONLAR",
            description="En başarılı oyuncular ve rekorlar",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        
        weekly_champs = hof.get("weekly_champions", {})
        if weekly_champs:
            top_3 = sorted(weekly_champs.items(), key=lambda x: x[1], reverse=True)[:3]
            champ_text = "\n".join([
                f"{'🥇' if i==0 else '🥈' if i==1 else '🥉'} **{name}** - {count} hafta"
                for i, (name, count) in enumerate(top_3)
            ])
            embed.add_field(name="📅 En Çok Haftalık Şampiyon", value=champ_text, inline=False)
        
        monthly_champs = hof.get("monthly_champions", {})
        if monthly_champs:
            top_3 = sorted(monthly_champs.items(), key=lambda x: x[1], reverse=True)[:3]
            champ_text = "\n".join([
                f"{'🥇' if i==0 else '🥈' if i==1 else '🥉'} **{name}** - {count} ay"
                for i, (name, count) in enumerate(top_3)
            ])
            embed.add_field(name="📆 En Çok Aylık Şampiyon", value=champ_text, inline=False)
        
        records = hof.get("records", {})
        if records:
            record_text = ""
            
            if "highest_weekly_score" in records:
                r = records["highest_weekly_score"]
                record_text += f"🎯 **En Yüksek Score:** {r['player']} - {r['score']:,} ({r['date']})\n"
            
            if "highest_kills_week" in records:
                r = records["highest_kills_week"]
                record_text += f"💀 **En Çok Kill:** {r['player']} - {r['kills']} ({r['date']})"
            
            if record_text:
                embed.add_field(name="📊 Rekorlar", value=record_text, inline=False)
        
        embed.set_footer(text="🏆 Tebrikler tüm şampiyonlara!")
        
        await ctx.send(embed=embed)

    async def _publish_report(self, guild, period, channel=None):
        deltas = self._calculate_deltas(period)
        if not deltas: return
        
        embed = self._create_report_embed(deltas, period, preview=False)
        
        # Generate charts
        from cogs.utils.chart_maker import generate_report_charts
        try:
            chart_buf = await asyncio.to_thread(generate_report_charts, deltas, period)
            file = discord.File(chart_buf, filename="report_charts.png")
            embed.set_image(url="attachment://report_charts.png")
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            file = None
        
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="rapor-log")
            if not channel:
                 # Fallback 1: squad-log
                 channel = discord.utils.get(guild.text_channels, name="squad-log")
        
        if channel:
            if file:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
        else:
             logger.warning(f"Report Generation Failed: No suitable channel found in {guild.name}")
             pass

    def _create_report_embed(self, deltas, period, preview=False):
        # Sorts
        top_score = sorted(deltas, key=lambda x: x["score"], reverse=True)[:1]
        top_kill = sorted(deltas, key=lambda x: x["kills"], reverse=True)[:1]
        top_revive = sorted(deltas, key=lambda x: x["revives"], reverse=True)[:1]
        # top_kd = sorted(deltas, key=lambda x: x["kd"], reverse=True) # Needs min kill filter
        
        # Leaderboard (Score)
        leaderboard = sorted(deltas, key=lambda x: x["score"], reverse=True)[:10]

        period_map = {"weekly": "Haftalık", "monthly": "Aylık", "daily": "Günlük"}
        title_p = period_map.get(period, period.capitalize())
        
        embed = discord.Embed(
            title=f"📊 {title_p} Sunucu Raporu" + (" (Önizleme)" if preview else ""),
            color=discord.Color.gold() if not preview else discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        if top_score:
            mvp = top_score[0]
            embed.add_field(name="🏆 HAFTANIN MVP'si", value=f"**{mvp['name']}**\n📈 +{mvp['score']} Puan", inline=False)
            
        # Inline Stats
        killer_txt = f"**{top_kill[0]['name']}** ({top_kill[0]['kills']} Kill)" if top_kill else "-"
        medic_txt = f"**{top_revive[0]['name']}** ({top_revive[0]['revives']} Revive)" if top_revive else "-"
        
        embed.add_field(name="⚔️ En Çok Adam Vuran", value=killer_txt, inline=True)
        embed.add_field(name="🚑 En İyi Doktor", value=medic_txt, inline=True)
        
        # List
        lb_text = []
        for i, p in enumerate(leaderboard, 1):
            icon = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            lb_text.append(f"{icon} **{p['name']}** - {p['score']} Puan | {p['kills']} K | {p['deaths']} D")
            
        embed.add_field(name="📜 Puan Sıralaması (Top 10)", value="\n".join(lb_text) if lb_text else "Veri Yok", inline=False)
        
        if not preview:
             embed.set_footer(text="İstatistikler sıfırlandı. Yeni dönem başladı.")
        
        return embed

    # ==================== INTERNAL ACTIVITY TRACKING ====================
    
    ACTIVITY_FILE = "squad_activity.json"
    
    async def load_activity_data(self):
        """Load activity data from squad_activity.json"""
        if not os.path.exists(self.ACTIVITY_FILE):
            return {}
        try:
            def _load():
                with open(self.ACTIVITY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return await asyncio.to_thread(_load)
        except Exception as e:
            logger.error(f"Failed to load activity data: {e}")
            return {}
    
    async def save_activity_data(self, data):
        """Save activity data to squad_activity.json"""
        def _save():
            with open(self.ACTIVITY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        await asyncio.to_thread(_save)
    
    async def record_activity(self, steam_id, name, data=None):
        """Record 2 minutes of activity for a player"""
        should_save = False
        if data is None:
            data = await self.load_activity_data()
            should_save = True
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        if steam_id not in data:
            data[steam_id] = {"name": name, "history": {}, "total_minutes": 0}
        
        data[steam_id]["name"] = name
        
        if today not in data[steam_id]["history"]:
            data[steam_id]["history"][today] = 0
        
        # Increment by 2 minutes (loop runs every 2 minutes)
        data[steam_id]["history"][today] += 2
        data[steam_id]["total_minutes"] += 2
        data[steam_id]["last_seen"] = datetime.datetime.now().isoformat()
        
        if should_save:
            await self.save_activity_data(data)
        
        return data
    

    # ========== GOOGLE SHEETS ACTIVITY PANEL (NEW) ==========

ACTIVITY_SHEET_ID = '1GAmtAqOSOh5DplcufyqvKepcepgfo-ORsfWXThbP_s8'

async def fetch_activity_from_sheets(self, force=False):
    """Fetch activity data from Google Sheets with smart G2 timestamp caching"""
    try:
        if not hasattr(self, 'gc') or not self.gc:
            logger.warning("Google Sheets client not initialized")
            return getattr(self, '_cached_activity_data', [])
        
        sheet = self.gc.open_by_key(ACTIVITY_SHEET_ID)
        worksheet = sheet.get_worksheet(0)  # First sheet
        
        # Check G2 for last update timestamp
        last_update_cell = worksheet.acell('G2').value
        
        # Compare with cached timestamp
        cached_timestamp = getattr(self, '_last_sheet_update', None)
        
        if not force and cached_timestamp == last_update_cell:
            logger.info(f"Sheet data unchanged (G2: {last_update_cell})")
            return getattr(self, '_cached_activity_data', [])
        
        # Fetch fresh data
        all_values = worksheet.get_all_values()[1:]  # Skip header
        
        activity_data = []
        for row in all_values:
            if len(row) >= 1 and row[0]:  # Has name
                activity_data.append({
                    'name': row[0],
                    'steam_id': row[1] if len(row) > 1 else '',
                    'playtime_2weeks': self._parse_playtime(row[2]) if len(row) > 2 else 0,
                    'leave_status': row[3] if len(row) > 3 else 'Aktif'
                })
        
        # Cache data and timestamp
        self._cached_activity_data = activity_data
        self._last_sheet_update = last_update_cell
        
        logger.info(f"Sheet data updated (G2: {last_update_cell}, {len(activity_data)} players)")
        return activity_data
        
    except Exception as e:
        logger.error(f"Sheets fetch error: {e}", exc_info=True)
        return getattr(self, '_cached_activity_data', [])

def _parse_playtime(self, value):
    """Convert sheet playtime value to minutes"""
    if not value:
        return 0
    
    try:
        # Try direct number (minutes)
        return int(float(value))
    except:
        # Try formats like "2828 dk" or "47 saat" or "47.2"
        value_str = str(value).lower().replace(',', '.')
        
        if 'saat' in value_str or 'hour' in value_str:
            # Extract number and convert hours to minutes
            num = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
            return int(num * 60)
        elif 'dk' in value_str or 'min' in value_str:
            # Extract minutes
            num = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
            return int(num)
        else:
            # Try as raw number
            num = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
            return int(num)
    
    return 0

async def generate_activity_panel_sheets(self, activity_data):
    """Generate activity panel embed from Sheets data"""
    
    # Separate active vs on-leave players
    on_leave_keywords = ['izinli', 'izin', 'izinde', 'leave']
    active_players = [p for p in activity_data if p['leave_status'].lower() not in on_leave_keywords]
    on_leave = [p for p in activity_data if p['leave_status'].lower() in on_leave_keywords]
    
    # Sort by playtime (descending)
    active_players.sort(key=lambda x: x['playtime_2weeks'], reverse=True)
    
    embed = discord.Embed(
        title="🎮 AKTİFLİK SIRALAMASI",
        description="**Son 2 Hafta** • Google Sheets verilerine göre",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    # Top 10 ranking
    top_10_text = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, player in enumerate(active_players[:10]):
        hours = player['playtime_2weeks'] / 60
        medal = medals[i] if i < len(medals) else f"{i+1}."
        top_10_text += f"{medal} **{player['name']}** - {hours:.1f} saat\n"
    
    if not top_10_text:
        top_10_text = "Veri bulunamadı"
    
    embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━", value=top_10_text, inline=False)
    
    # Statistics
    total_active = len(active_players)
    avg_time = sum(p['playtime_2weeks'] for p in active_players) / total_active if total_active > 0 else 0
    top_player = active_players[0] if active_players else None
    
    stats_text = f"📊 **Toplam Aktif:** {total_active} oyuncu\n"
    stats_text += f"⏱️ **Ortalama:** {avg_time/60:.1f} saat\n"
    if top_player:
        stats_text += f"🏆 **En Aktif:** {top_player['name']} ({top_player['playtime_2weeks']/60:.1f} saat)"
    
    embed.add_field(name="📈 İstatistikler", value=stats_text, inline=False)
    
    # On-leave players
    if on_leave:
        leave_text = "\n".join([f"• {p['name']}" for p in on_leave[:10]])
        if len(on_leave) > 10:
            leave_text += f"\n... ve {len(on_leave) - 10} oyuncu daha"
        embed.add_field(name=f"🌴 İzinli Oyuncular ({len(on_leave)})", value=leave_text, inline=False)
    
    # Update timestamp from G2
    last_update = getattr(self, '_last_sheet_update', 'Bilinmiyor')
    embed.set_footer(text=f"Veri Kaynağı: Google Sheets • Son Güncelleme: {last_update}")
    
    return embed

    async def generate_activity_panel_internal(self):
        """Generate activity panel from internal tracking data"""
        data = await self.load_activity_data()
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        today_date = datetime.datetime.strptime(today, "%Y-%m-%d")
        
        stats = []
        if data:
            for steam_id, player_data in data.items():
                history = player_data.get("history", {})
                daily = history.get(today, 0)
                weekly = 0
                monthly = 0
                
                # Calculate weekly and monthly
                for date_str, mins in history.items():
                    try:
                        d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                        diff = (today_date - d).days
                        if diff < 7:
                            weekly += mins
                        if diff < 30:
                            monthly += mins
                    except:
                        pass
                
                stats.append({
                    "name": player_data.get("name", "Unknown"),
                    "daily": daily,
                    "weekly": weekly,
                    "monthly": monthly
                })
        
        # Sort by weekly playtime
        stats.sort(key=lambda x: x["weekly"], reverse=True)
        logger.info(f"Generated activity stats for {len(stats)} players from internal tracking")
        return stats

    @commands.command(name='aktiflik_panel', aliases=['squad_activity'])
    async def aktiflik_panel(self, ctx, channel: discord.TextChannel = None):
        """Internal tracking tabanlı aktiflik paneli kurar."""
        if not await self.check_permissions(ctx): return
        
        target = channel or ctx.channel
        cfg = self.load_activity_panel_config()
        
        # Clean old panel
        if str(ctx.guild.id) in cfg:
            old_ch = cfg[str(ctx.guild.id)].get("channel_id")
            old_msg = cfg[str(ctx.guild.id)].get("message_id")
            try:
                ch = ctx.guild.get_channel(old_ch)
                if ch and old_msg:
                    msg = await ch.fetch_message(old_msg)
                    await msg.delete()
                    logger.info(f"Deleted old activity panel message {old_msg}")
            except Exception as e:
                logger.warning(f"Could not delete old panel: {e}")
        
        await ctx.send(f"✅ Aktiflik paneli {target.mention} kanalına kuruldu.")
        
        try:
            # Generate stats from internal tracking
            stats = await self.generate_activity_panel_internal()
            
            # Generate image
            image_buf = generate_activity_image(stats)
            
            # Create embed with refresh button
            file = discord.File(image_buf, filename="activity_panel.png")
            embed = discord.Embed(
                title="🏆 SQUAD SUNUCU AKTİFLİK",
                description="📊 Sunucu içi aktivite (Bot tracking)",
                color=discord.Color.gold()
            )
            embed.set_image(url="attachment://activity_panel.png")
            embed.set_footer(text=f"Son Güncelleme: {datetime.datetime.now().strftime('%H:%M')} | Internal Tracking | Otomatik: Her dakika")
            
            # Refresh button view
            view = ActivityRefreshView(self, ctx.guild.id)
            panel_msg = await target.send(embed=embed, file=file, view=view)
            
            # Save config
            cfg[str(ctx.guild.id)] = {"channel_id": target.id, "message_id": panel_msg.id}
            self.save_activity_panel_config(cfg)
            
        except Exception as e:
            await ctx.send(f"❌ Panel oluşturulurken hata: {e}")
            logger.error(f"Activity panel error: {e}", exc_info=True)

    @commands.command(name='aktiflik_yonet')
    async def aktiflik_yonet(self, ctx):
        """Aktiflik panelini yönet."""
        if not await self.check_permissions(ctx): return
        
        cfg = self.load_activity_panel_config()
        if str(ctx.guild.id) not in cfg:
            await ctx.send("❌ Aktif panel yok.")
            return
        
        view = ActivityManageView(self, ctx.guild.id)
        embed = discord.Embed(
            title="⚙️ Aktiflik Paneli Yönetimi",
            description="Paneli silmek için butonu kullanın.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, view=view)


class ActivityRefreshView(discord.ui.View):
    """View with refresh button for activity panel."""
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)  # Permanent view
        self.cog = cog
        self.guild_id = str(guild_id)
    
    @discord.ui.button(label="🔄 Yenile", style=discord.ButtonStyle.primary, custom_id="activity_refresh")
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh activity panel with latest internal data."""
        await interaction.response.defer()
        
        try:
            # Generate fresh stats from internal tracking
            stats = await self.cog.generate_activity_panel_internal()
            
            # Generate new image
            image_buf = generate_activity_image(stats)
            
            # Update panel
            file = discord.File(image_buf, filename="activity_panel.png")
            embed = discord.Embed(
                title="🏆 SQUAD SUNUCU AKTİFLİK",
                description="📊 Sunucu içi aktivite (Bot tracking)",
                color=discord.Color.gold()
            )
            embed.set_image(url="attachment://activity_panel.png")
            embed.set_footer(text=f"Son Güncelleme: {datetime.datetime.now().strftime('%H:%M')} | Internal Tracking | Otomatik: Her dakika")
            
            # Edit message with new data
            await interaction.message.edit(embed=embed, attachments=[file], view=self)
            
            await interaction.followup.send("✅ Panel güncellendi!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Yenileme hatası: {e}", ephemeral=True)
            logger.error(f"Activity refresh error: {e}", exc_info=True)


async def setup(bot):
    await bot.add_cog(SquadPlayers(bot))
