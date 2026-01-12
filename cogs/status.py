import discord
from discord.ext import commands
import datetime
import os
import json
import time
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def check_permissions(self, ctx_or_int):
        # Centralized Admin Check (Similar to squad.py)
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

    @commands.command(name='bot_durum')
    async def system_status(self, ctx):
        """Botun ve modüllerin genel sağlık durumunu gösterir."""
        if not await self.check_permissions(ctx): return

        embed = discord.Embed(title="🏥 Bot Sağlık Durumu", color=discord.Color.blue())
        embed.set_footer(text=f"Sorgu: {datetime.datetime.now().strftime('%H:%M:%S')}")

        # 1. API & Latency
        latency_ms = round(self.bot.latency * 1000)
        status_icon = "🟢" if latency_ms < 200 else ("🟡" if latency_ms < 500 else "🔴")
        embed.add_field(name="📶 Bağlantı (Ping)", value=f"{status_icon} `{latency_ms}ms`", inline=True)

        # 2. Database Check
        db_status = "🔴 Okunamadı"
        if os.path.exists("squad_db.json"):
            try:
                with open("squad_db.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    count = len(data.get("players", []))
                    db_status = f"🟢 Aktif ({count} Kayıt)"
            except:
                db_status = "🟡 Bozuk JSON"
        else:
            db_status = "⚪ Dosya Yok"
        embed.add_field(name="💾 Veritabanı", value=db_status, inline=True)
        
        # Spacer
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        # 3. Module Status (Loops)
        # Squad Modules
        squad_server = self.bot.get_cog('SquadServer')
        squad_players = self.bot.get_cog('SquadPlayers')
        
        server_txt = "⚪ Yüklü Değil"
        players_txt = "⚪ Yüklü Değil"
        
        if squad_server:
            live_loop = "🟢" if squad_server.live_panel_loop.is_running() else "🔴"
            server_txt = f"Live Panel: {live_loop}"

        if squad_players:
            auto_sync = "🟢" if squad_players.auto_sync_loop.is_running() else "🔴"
            activity_loop = "🟢" if squad_players.activity_panel_loop.is_running() else "🔴"
            players_txt = f"Sync: {auto_sync} | Activity: {activity_loop}"

        embed.add_field(name="🎮 Squad Sunucu", value=server_txt, inline=True)
        embed.add_field(name="👥 Squad Oyuncu", value=players_txt, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False) # Newline

        # Event Module
        event_cog = self.bot.get_cog('Event')
        event_txt = "⚪ Yüklü Değil"
        if event_cog:
            # Assuming 'check_events_task' exists in Event cog
            try:
                loop_status = "🟢" if event_cog.check_events_task.is_running() else "🔴"
                event_txt = f"Etkinlik Döngüsü: {loop_status}"
            except AttributeError:
                event_txt = "🟡 Döngü Bulunamadı"
        embed.add_field(name="📅 Etkinlik Sistemi", value=event_txt, inline=False)

        # Voice Stats Module
        voice_cog = self.bot.get_cog('VoiceStats') # Verify class name later if needed
        voice_txt = "⚪ Yüklü Değil"
        if voice_cog:
            try:
                # Assuming 'save_stats_loop' exists
                loop_status = "🟢" if voice_cog.save_stats_loop.is_running() else "🔴"
                voice_txt = f"İstatistik Kayıt: {loop_status}"
            except AttributeError:
                voice_txt = "🟡 Döngü Bulunamadı"
        embed.add_field(name="🎤 Ses İstatistikleri", value=voice_txt, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
