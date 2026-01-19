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
        """Botun ve modüllerin detaylı sağlık durumunu gösterir."""
        if not await self.check_permissions(ctx): return
        
        status_msg = await ctx.send("🏥 **Durum analizi yapılıyor...**")

        embed = discord.Embed(title="🏥 Cotabot Sistem Durumu", color=discord.Color.blue())
        embed.set_footer(text=f"Analiz Zamanı: {datetime.datetime.now().strftime('%H:%M:%S')}")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # 1. API & Latency
        latency_ms = round(self.bot.latency * 1000)
        status_icon = "🟢" if latency_ms < 200 else ("🟡" if latency_ms < 500 else "🔴")
        embed.add_field(name="📶 API Gecikmesi", value=f"{status_icon} `{latency_ms}ms`", inline=True)
        
        # 2. Database Connection
        db_status = "🔴 Bağlantı Yok"
        db_details = "N/A"
        
        squad_players = self.bot.get_cog('SquadPlayers')
        db = getattr(squad_players, 'db', None) if squad_players else None
        
        if db:
            try:
                # Active Ping Test
                start = time.time()
                # Simple query to check responsiveness
                await db.get_player_by_steam_id("0") 
                db_latency = round((time.time() - start) * 1000)
                
                db_status = f"🟢 Aktif (`{db_latency}ms`)"
                
                # Fetch Counts
                p_count = len(await db.get_all_players())
                active_events = len(await db.get_active_events(ctx.guild.id)) if ctx.guild else 0
                
                db_details = f"👥 **Oyuncula:** {p_count}\n📅 **Aktif Etkinlik:** {active_events}"
            except Exception as e:
                db_status = f"🟡 Hata: {str(e)[:20]}"
        
        embed.add_field(name="💾 Veritabanı", value=db_status, inline=True)
        embed.add_field(name="📚 Veri Özeti", value=db_details, inline=True)

        # 3. Module Status & Loops
        squad_server = self.bot.get_cog('SquadServer')
        
        modules_text = ""
        
        # Squad Server
        if squad_server:
            loop_status = "🟢 Çalışıyor" if squad_server.live_panel_loop.is_running() else "🔴 Durmuş"
            modules_text += f"**Squad Server:** {loop_status}\n"
        else:
            modules_text += "**Squad Server:** ⚪ Yüklü Değil\n"
            
        # Squad Players
        if squad_players:
            track_status = "🟢 Çalışıyor" if squad_players.activity_tracker_loop.is_running() else "🔴 Durmuş"
            sync_status = "🟢 Çalışıyor" if squad_players.auto_sync_loop.is_running() else "🔴 Durmuş"
            
            modules_text += f"**Aktivite Takip:** {track_status}\n"
            modules_text += f"**Auto Sync:** {sync_status}\n"
            
            # Last Activity Log check
            if hasattr(squad_players, 'json_mode'):
                mode = "JSON (Eski)" if squad_players.json_mode else "SQLite (Yeni)"
                modules_text += f"**Mod:** {mode}"
        else:
            modules_text += "**Squad Players:** ⚪ Yüklü Değil"
            
        embed.add_field(name="⚙️ Modüller ve Döngüler", value=modules_text, inline=False)
        
        # 4. System Info
        import platform
        sys_info = f"Python: {platform.python_version()}\nOS: {platform.system()} {platform.release()}"
        embed.add_field(name="💻 Sistem", value=sys_info, inline=True)
        
        await status_msg.edit(content=None, embed=embed)

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
