import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import math
import logging

# Database import
from database.adapter import DatabaseAdapter

# Logger setup
logger = logging.getLogger('VoiceStats')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
logger.addHandler(handler)

STATS_FILE = "voice_stats.json"  # Deprecated, keeping for migration reference

class VoiceStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Database adapter
        self.db = DatabaseAdapter('sqlite:///cotabot_dev.db')
        self.db.init_db()
        # Active session IDs: {user_id: session_db_id}
        self.active_sessions = {}
        logger.info("VoiceStats initialized with database")

    def cog_unload(self):
        logger.info("VoiceStats unloaded.")

    # Deprecated - keeping for migration script reference
    def load_stats(self):
        if not os.path.exists(STATS_FILE):
            return {}
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
            return {}

    # Deprecated - sessions are now tracked in database on join/leave
    # No periodic loop needed
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot açıldığında seste olanları tespit et ve sessions başlat."""
        logger.info("VoiceStats scanning for active users...")
        count = 0
        
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if not member.bot:
                        # Start database session
                        try:
                            session_id = await self.db.start_voice_session(
                                guild_id=guild.id,
                                user_id=member.id,
                                channel_id=vc.id,
                                channel_name=vc.name
                            )
                            self.active_sessions[member.id] = session_id
                            count += 1
                        except Exception as e:
                            logger.error(f"Error starting session for {member.display_name}: {e}")
                            
        if count > 0:
            logger.info(f"{count} users detected in voice and tracking started")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

        user_id = member.id
        guild_id = member.guild.id
        
        # 1. KANAL DEĞİŞİMİ veya ÇIKIŞ (Eski oturumu kapat)
        if before.channel is not None:
            if user_id in self.active_sessions:
                session_id = self.active_sessions.pop(user_id)
                
                # Calculate coins earned (1 coin per 60 seconds, AFK channel = 0)
                is_afk = before.channel.name == "AFK"
                
                try:
                    # End session in database
                    duration = await self.db.end_voice_session(session_id, coins_earned=0)
                    
                    # Update balance
                    if not is_afk and duration > 0:
                        coins_earned = int(duration // 60)
                        pending_secs = duration % 60
                        
                        await self.db.update_voice_balance(
                            guild_id=guild_id,
                            user_id=user_id,
                            coins_delta=coins_earned,
                            pending_secs_delta=pending_secs,
                            duration_delta=duration
                        )
                    else:
                        # AFK or no time - just update total time
                        await self.db.update_voice_balance(
                            guild_id=guild_id,
                            user_id=user_id,
                            duration_delta=duration if duration > 0 else 0
                        )
                    
                    logger.debug(f"Session ended: {member.display_name} in {before.channel.name}, {duration:.1f}s")
                except Exception as e:
                    logger.error(f"Error ending session: {e}")

        # 2. GİRİŞ (Yeni oturum başlat)
        if after.channel is not None:
            if before.channel != after.channel:  # New join or channel switch
                try:
                    session_id = await self.db.start_voice_session(
                        guild_id=guild_id,
                        user_id=user_id,
                        channel_id=after.channel.id,
                        channel_name=after.channel.name
                    )
                    self.active_sessions[user_id] = session_id
                    logger.debug(f"Session started: {member.display_name} in {after.channel.name}")
                except Exception as e:
                    logger.error(f"Error starting session: {e}")

    def format_duration(self, seconds):
        if seconds < 60:
            return f"{int(seconds)} sn"
        
        minutes = math.floor(seconds / 60)
        hours = math.floor(minutes / 60)
        minutes = minutes % 60
        
        if hours > 0:
            return f"{hours} sa {minutes} dk"
        else:
            return f"{minutes} dk"

    @commands.command(name='stat')
    async def stat(self, ctx, member: discord.Member = None):
        """Kullanıcının detaylı ses istatistiğini gösterir."""
        try:
            target = member or ctx.author
            guild_id = ctx.guild.id
            
            # Get stats from database
            stats = await self.db.get_user_voice_stats(guild_id, target.id)
            balance_obj = await self.db.get_voice_balance(guild_id, target.id)
            
            total_seconds = stats["total_seconds"]
            
            # Add active session time if currently in voice
            active_session_seconds = 0
            if target.id in self.active_sessions:
                # Get session from database would be ideal, but we can calculate from local start time if needed
                # For accuracy, let's just use what we have in DB + current delta if we track start time locally
                # But active_sessions now holds DB ID, not start time.
                # So we fetch active session from DB
                session = await self.db.get_active_session(guild_id, target.id)
                if session:
                    active_session_seconds = (datetime.datetime.now() - session.joined_at).total_seconds()
                    total_seconds += active_session_seconds
            
            formatted_total = self.format_duration(total_seconds)

            embed = discord.Embed(
                title=f"📊 Ses İstatistikleri: {target.display_name}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="Toplam Süre", value=f"**{formatted_total}**", inline=False)
            
            # En çok vakit geçirilen kanallar (Top 5)
            channels_data = stats.get("channels", {})
            
            if channels_data:
                # Sırala
                sorted_channels = sorted(
                    channels_data.items(), 
                    key=lambda item: item[1]['seconds'], 
                    reverse=True
                )
                
                top_channels_text = ""
                for i, (cid, cdata) in enumerate(sorted_channels[:5], 1):
                    c_name = cdata['name']
                    c_time = self.format_duration(cdata['seconds'])
                    top_channels_text += f"**{i}.** {c_name}: `{c_time}`\n"
                
                embed.add_field(name="En Çok Takılınan Kanallar", value=top_channels_text, inline=False)

            if active_session_seconds > 0:
                embed.set_footer(text="🟢 Şu an aktif (Süreler dahil edildi)")
                
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Stat komutunda hata: {e}")
            logger.error(f"Stat Error: {e}", exc_info=True)

    @commands.command(name='cüzdan', aliases=['wallet', 'coin', 'bakiye'])
    async def cuzdan(self, ctx, member: discord.Member = None):
        """Mevcut CotaSüre (bakiye) durumunu gösterir."""
        target = member or ctx.author
        guild_id = ctx.guild.id
        
        # Get balance from database
        balance_obj = await self.db.get_voice_balance(guild_id, target.id)
        
        balance = balance_obj.balance
        total_time = balance_obj.total_time_seconds
        formatted_time = self.format_duration(total_time)
        
        embed = discord.Embed(
            title=f"💰 Cüzdan: {target.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💸 Bakiye", value=f"**{balance} CotaSüre**", inline=True)
        embed.add_field(name="🎙️ Toplam Ses", value=f"{formatted_time}", inline=True)
        embed.set_footer(text="Seste kaldığın her dakika için 1 CotaSüre kazanırsın!")
        
        await ctx.send(embed=embed)

    @commands.command(name='transfer')
    async def transfer(self, ctx, recipient: discord.Member, amount: int):
        """Başka bir kullanıcıya CotaSüre gönderir."""
        if amount <= 0:
            await ctx.send("❌ Hata: Gönderilecek miktar 0'dan büyük olmalıdır.")
            return
        
        if recipient.id == ctx.author.id:
            await ctx.send("❌ Kendine transfer yapamazsın.")
            return

        guild_id = ctx.guild.id
        
        # Check balance
        sender_balance = await self.db.get_voice_balance(guild_id, ctx.author.id)
        
        if sender_balance.balance < amount:
            await ctx.send(f"❌ Yetersiz bakiye. Mevcut: {sender_balance.balance} CotaSüre")
            return
        
        # Transfer coins
        success = await self.db.transfer_voice_coins(
            guild_id=guild_id,
            sender_id=ctx.author.id,
            receiver_id=recipient.id,
            amount=amount
        )
        
        if success:
            # Get updated balance
            new_balance = await self.db.get_voice_balance(guild_id, ctx.author.id)
            await ctx.send(f"✅ Başarılı! **{recipient.display_name}** kullanıcısına **{amount} CotaSüre** gönderildi.\n"
                           f"📉 Yeni Bakiyen: {new_balance.balance}")
        else:
            await ctx.send("❌ Transfer başarısız.")

    @commands.command(name='debug_sessions')
    async def debug_sessions(self, ctx):
        """(Admin) Aktif ses oturumlarını gösterir."""
        if not ctx.author.guild_permissions.administrator: return
        
        active_count = len(self.active_sessions)
        msg = f"🔍 **Aktif Oturumlar (DB IDs):** {active_count}\n"
        for uid, session_id in self.active_sessions.items():
            member = ctx.guild.get_member(uid)
            name = member.display_name if member else f"Unknown ({uid})"
            msg += f"- {name}: Session #{session_id}\n"
            
        await ctx.send(msg)

    @commands.command(name='top10')
    async def top10(self, ctx):
        """Sunucudaki en çok ses süresine sahip 10 kişiyi gösterir."""
        guild_id = ctx.guild.id
        
        # Get leaderboard from database
        leaderboard = await self.db.get_voice_leaderboard(guild_id, limit=10)
        
        if not leaderboard:
            await ctx.send("Henüz kayıtlı istatistik yok.")
            return

        description_lines = []
        for index, entry in enumerate(leaderboard, 1):
            user_id = entry["user_id"]
            seconds = entry["total_seconds"]
            
            user = ctx.guild.get_member(user_id)
            name = user.display_name if user else f"Kullanıcı ({user_id})"
            time_str = self.format_duration(seconds)
            
            medal = ""
            if index == 1: medal = "🥇"
            elif index == 2: medal = "🥈"
            elif index == 3: medal = "🥉"
            else: medal = f"**{index}.**"
            
            description_lines.append(f"{medal} **{name}**: {time_str}")

        embed = discord.Embed(
            title="🏆 Ses Sıralaması (Top 10)",
            description="\n".join(description_lines),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    print("DEBUG: VoiceStats Cog Loading...")
    await bot.add_cog(VoiceStats(bot))
    print("DEBUG: VoiceStats Cog Loaded!")
