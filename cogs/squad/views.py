"""
Squad Players - UI Views
Oyuncu yönetimi, sıralama ve aktivite paneli için Discord UI Views
"""
import discord
from discord.ext import commands
import os
import datetime
import json
import asyncio
import logging

from ..utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, COLORS
from ..utils.pagination import PaginationView

logger = logging.getLogger("SquadPlayers.Views")


class PlayerSelectView(discord.ui.View):
    """Oyuncu seçimi için dropdown view"""
    def __init__(self, bot, players):
        super().__init__(timeout=180)
        self.bot = bot
        self.players = players  # Store for later use
        options = []
        for p in players:
            label = p['name'][:100]
            desc = f"SID: {p['steam_id']}"
            options.append(discord.SelectOption(label=label, description=desc, value=p['steam_id']))
        
        self.add_item(PlayerSelectDropdown(bot, options, players))


class PlayerSelectDropdown(discord.ui.Select):
    """Oyuncu seçimi dropdown menüsü"""
    def __init__(self, bot, options, players):
        self.bot = bot
        self.players = players  # Store player data
        super().__init__(placeholder="Bir oyuncu seçin...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        steam_id = self.values[0]
        
        # Use cached player data
        target_player = None
        for p in self.players:
            if p.get("steam_id") == steam_id:
                target_player = p
                break
        
        # JSON fallback if not found
        if not target_player and os.path.exists("squad_db.json"):
            try:
                def _find_player():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for p in data.get("players", []):
                            if p["steam_id"] == steam_id: 
                                return p
                    return None
                target_player = await asyncio.to_thread(_find_player)
            except: 
                pass
            
        if not target_player:
            await interaction.response.send_message(
                "❌ Oyuncu veritabanında bulunamadı (silinmiş olabilir).", 
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"👤 Oyuncu Bilgisi: {target_player['name']}", 
            color=discord.Color(COLORS.SQUAD)
        )
        embed.add_field(name="Steam ID", value=f"`{target_player['steam_id']}`", inline=False)
        embed.add_field(name="Discord ID", value=f"`{target_player.get('discord_id', '-')}`", inline=False)
        
        view = PlayerActionView(self.bot, target_player)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PlayerActionView(discord.ui.View):
    """Oyuncu için düzenle/sil butonları"""
    def __init__(self, bot, player_data):
        super().__init__(timeout=180)
        self.bot = bot
        self.player_data = player_data

    @discord.ui.button(label="✏️ Düzenle", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .modals import PlayerAddModal
        
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
        
        # HYBRID MODE: Try SQLite first
        cog = self.bot.get_cog("SquadPlayers")
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            try:
                # Delete from database
                deleted = await cog.db.delete_player(s_id)
                if deleted:
                    # Log to channel
                    await cog.log_to_channel(
                        interaction.guild, 
                        "🗑️ Oyuncu Silindi (DB)", 
                        f"**Oyuncu:** {name}\n**SteamID:** `{s_id}`", 
                        interaction.user, 
                        color=COLORS.ERROR
                    )
                    
                    await interaction.response.send_message(
                        f"✅ **{name}** ({s_id}) başarıyla silindi (DB).", 
                        ephemeral=True
                    )
                    return  # Exit - database handled it
            except Exception as e:
                logger.error(f"DB delete error: {e}, fallback to JSON")
        
        # JSON mode or fallback
        if os.path.exists(db_file):
            try:
                def _delete_logic():
                    with open(db_file, "r", encoding="utf-8") as f: 
                        data = json.load(f)
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
            except: 
                pass
            
            # Log to Channel
            cog = self.bot.get_cog("SquadPlayers")
            if cog:
                await cog.log_to_channel(
                    interaction.guild, 
                    "🗑️ Oyuncu Silindi", 
                    f"**Oyuncu:** {name}\n**SteamID:** `{s_id}`", 
                    interaction.user, 
                    color=COLORS.ERROR
                )
            
            await interaction.response.send_message(
                f"✅ **{name}** ({s_id}) başarıyla silindi.", 
                ephemeral=True
            )
            
            # Sync to Sheet
            if cog:
                asyncio.create_task(cog.update_sheet_player(s_id, name, None, delete=True))
        else:
            await interaction.response.send_message(
                "❌ Silme işlemi başarısız (Zaten silinmiş olabilir).", 
                ephemeral=True
            )


class PlayerManageView(discord.ui.View):
    """Ana oyuncu yönetim paneli"""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    def check_auth(self, interaction):
        """Yetki kontrolü"""
        if interaction.user.guild_permissions.administrator: 
            return True
        if interaction.user.id in ADMIN_USER_IDS: 
            return True
        for r in interaction.user.roles:
            if r.id in ADMIN_ROLE_IDS: 
                return True
        return False

    @discord.ui.button(
        label="🔎 Oyuncu Ara (Düzenle/Sil)", 
        style=discord.ButtonStyle.primary, 
        row=0, 
        custom_id="pm_search_player"
    )
    async def search_player_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_auth(interaction): 
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
            return
        
        from .modals import PlayerSearchModal
        modal = PlayerSearchModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="➕ Oyuncu Ekle", 
        style=discord.ButtonStyle.green, 
        row=1, 
        custom_id="pm_add_player"
    )
    async def add_player_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_auth(interaction): 
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
            return
        
        from .modals import PlayerAddModal
        modal = PlayerAddModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="💾 Veritabanı İndir", 
        style=discord.ButtonStyle.secondary, 
        row=1, 
        custom_id="pm_download_db"
    )
    async def download_db_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Sadece yöneticiler indirebilir.", ephemeral=True)
            return
        if os.path.exists("squad_db.json"):
            await interaction.response.send_message(file=discord.File("squad_db.json"), ephemeral=True)
        else:
            await interaction.response.send_message("❌ Veritabanı dosyası yok.", ephemeral=True)


class SquadLeaderboardView(PaginationView):
    """İstatistik sıralama tablosu (pagination + sort)"""
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

        self.all_players = players
        self.sort_players(players)
        
        # Init Pagination with sorted data
        super().__init__(
            data=self.data, 
            title=self.title_prefix, 
            page_size=10, 
            refresh_callback=refresh_callback
        )

    def sort_players(self, players_list):
        """Oyuncuları seçili kritere göre sırala"""
        stats_key = "stats" if self.mode == "AllTime" else "season_stats"
        prefix = "total" if self.mode == "AllTime" else "season"

        def get_sort_value(p):
            st = p.get(stats_key, {})
            if not st: 
                return 0
            val = st.get(self.sort_key, 0)
            try: 
                return float(val)
            except: 
                return 0
        
        self.data = sorted(players_list, key=get_sort_value, reverse=True)

    def get_current_embed(self):
        """Custom formatted embed with rankings"""
        exclude_start = self.current_page * self.page_size
        exclude_end = exclude_start + self.page_size
        page_items = self.data[exclude_start:exclude_end]

        embed = discord.Embed(
            title=f"{self.title_prefix}", 
            description=f"📂 **Sıralama Kriteri:** {self.sort_name}",
            color=self.color
        )
        timestamp = datetime.datetime.now().strftime('%H:%M')
        embed.set_footer(
            text=f"Mod: {self.mode} | Sayfa {self.current_page + 1}/{self.total_pages} | Güncelleme: {timestamp}"
        )

        stats_key = "stats" if self.mode == "AllTime" else "season_stats"
        prefix = "total" if self.mode == "AllTime" else "season"

        def get_stat(p, key_suffix, default=0):
            st = p.get(stats_key, {})
            if not st: 
                return default
            full_key = f"{prefix}{key_suffix}"
            if key_suffix == "KdRatio": 
                full_key = f"{prefix}KdRatio" 
            val = st.get(full_key, default)
            try: 
                return float(val)
            except: 
                return default

        for i, p in enumerate(page_items, exclude_start + 1):
            score = int(get_stat(p, "Score"))
            kills = int(get_stat(p, "Kills"))
            deaths = int(get_stat(p, "Deaths"))
            revives = int(get_stat(p, "Revives"))
            kd = get_stat(p, "KdRatio", 0.0)
            kd_str = f"{kd:.2f}"
            
            rank_display = f"#{i}"
            if i == 1: 
                rank_display = "🥇"
            elif i == 2: 
                rank_display = "🥈"
            elif i == 3: 
                rank_display = "🥉"
            elif i <= 5: 
                rank_display = f"Top {i} 🎖️"
            
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
        """Re-calculate totals and update view"""
        self.total_pages = max(1, (len(self.data) + self.page_size - 1) // self.page_size)
        self.current_page = 0  # Reset to first page on sort/filter change
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    # Custom buttons for pagination and sorting
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
        self.sort_players(self.data)
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
    """Aktivite paneli yönetimi"""
    def __init__(self, cog, guild_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild_id = str(guild_id)

    @discord.ui.button(label="🗑️ Aktiflik Panelini Sil", style=discord.ButtonStyle.danger)
    async def delete_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_permissions(interaction): 
            return

        cfg = self.cog.load_activity_panel_config()
        if self.guild_id in cfg:
            try:
                g_cfg = cfg[self.guild_id]
                ch = interaction.guild.get_channel(g_cfg["channel_id"])
                if ch:
                    msg = await ch.fetch_message(g_cfg["message_id"])
                    await msg.delete()
            except: 
                pass
            
            del cfg[self.guild_id]
            self.cog.save_activity_panel_config(cfg)
            await interaction.response.edit_message(
                content="✅ Aktiflik paneli silindi.", 
                embed=None, 
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="❌ Panel bulunamadı.", 
                embed=None, 
                view=None
            )
