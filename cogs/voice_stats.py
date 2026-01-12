import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import math
import logging

# Logger setup
logger = logging.getLogger('VoiceStats')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
logger.addHandler(handler)

STATS_FILE = "voice_stats.json"

class VoiceStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats = self.load_stats()
        # Anlık aktif oturumlar: {user_id: start_time(datetime)}
        self.active_sessions = {}
        self.save_stats_loop.start()

    def cog_unload(self):
        self.save_stats_loop.cancel()
        self.save_stats() # Force save on unload/restart
        logger.info("VoiceStats unloaded and data saved.")

    def load_stats(self):
        if not os.path.exists(STATS_FILE):
            return {}
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # MİGRASYON KONTROLÜ: Eski format (int/float) veriyi yeni yapıya çevir
            migrated = False
            new_data = {}
            for uid, value in data.items():
                if isinstance(value, (int, float)):
                    # Eski format: "uid": 120.5
                    new_data[uid] = {
                        "total_time": value,
                        "channels": {} # Eski verinin hangi kanaldan geldiğini bilemeyiz
                    }
                    migrated = True
                else:
                    # Yeni format zaten
                    new_data[uid] = value
            
            if migrated:
                print("DEBUG: Eski veri formatı yeni yapıya dönüştürüldü.")
                # Migrasyonu hemen kaydetmek isteyebiliriz ama save_stats çağrıldığında zaten olacak.
                # Şimdilik memory'de kalsın, ilk update'de diske yazılır.
            
            return new_data
        except Exception as e:
            print(f"Stats yüklenirken hata: {e}")
            return {}

    def save_stats(self):
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=4)

    def update_user_time(self, user_id, duration_seconds, channel_id=None, channel_name="Bilinmiyor", save=True):
        uid = str(user_id)
        if uid not in self.stats:
            self.stats[uid] = {
                "total_time": 0,
                "balance": 0,
                "pending_seconds": 0,
                "channels": {}
            }
        
        # Ensure migration for existing users
        if "balance" not in self.stats[uid]: self.stats[uid]["balance"] = 0
        if "pending_seconds" not in self.stats[uid]: self.stats[uid]["pending_seconds"] = 0
        
        # Genel toplamı güncelle (AFK olsa bile süre sayalım mı? Genelde evet, süre geçmişte kalsın ama ödül yok)
        self.stats[uid]["total_time"] += duration_seconds
        
        # COIN SİSTEMİ (CotaSüre)
        # AFK kanalındaysa kazanım yok
        is_afk = channel_name == "AFK"
        if not is_afk:
            self.stats[uid]["pending_seconds"] += duration_seconds
            
            # Her 60 saniyede 1 CotaSüre
            if self.stats[uid]["pending_seconds"] >= 60:
                earned = int(self.stats[uid]["pending_seconds"] // 60)
                self.stats[uid]["balance"] += earned
                self.stats[uid]["pending_seconds"] -= (earned * 60)
        
        # Kanal bazlı güncelleme
        if channel_id:
            cid = str(channel_id)
            if cid not in self.stats[uid]["channels"]:
                self.stats[uid]["channels"][cid] = {
                    "total_time": 0,
                    "name": channel_name
                }
            self.stats[uid]["channels"][cid]["total_time"] += duration_seconds
            # Kanal adını güncelle (değişmiş olabilir)
            self.stats[uid]["channels"][cid]["name"] = channel_name

        if save:
            self.save_stats()

    @tasks.loop(minutes=1)
    async def save_stats_loop(self):
        """Her dakika istatistikleri günceller ve kaydeder."""
        now = datetime.datetime.now()
        data_changed = False
        
        # DEBUG: Check if loop is running and detecting users
        logger.debug(f"save_stats_loop running. Active Sessions: {len(self.active_sessions)}")
        
        # Aktif olan herkesi güncelle
        # Modifikasyon hatası almamak için listeye çevirip dönüyoruz
        for user_id, start_time in list(self.active_sessions.items()):
            duration = (now - start_time).total_seconds()
            
            # Kanal bilgisini bulmaya çalış
            guild = self.bot.guilds[0] if self.bot.guilds else None
            member = guild.get_member(user_id) if guild else None
            
            c_id = None
            c_name = "Bilinmiyor"
            
            if member and member.voice and member.voice.channel:
                c_id = member.voice.channel.id
                c_name = member.voice.channel.name
            
            self.update_user_time(user_id, duration, c_id, c_name, save=False)
            
            # Sayacı sıfırla (Şu andan itibaren tekrar saymaya başla)
            self.active_sessions[user_id] = now
            data_changed = True
            
        if data_changed:
            self.save_stats()
            # print("DEBUG: Periyodik kayıt tamamlandı.")

    @save_stats_loop.before_loop
    async def before_save_stats(self):
        await self.bot.wait_until_ready()
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot açıldığında seste olanları tespit et."""
        print("DEBUG: VoiceStats taraması yapılıyor...")
        count = 0
        now = datetime.datetime.now()
        
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if not member.bot:
                        if member.id not in self.active_sessions:
                            self.active_sessions[member.id] = now
                            count += 1
                            
        if count > 0:
            print(f"DEBUG: {count} kullanıcı seste tespit edildi ve takibe alındı.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

        user_id = member.id
        now = datetime.datetime.now()
        
        # 1. KANAL DEĞİŞİMİ veya ÇIKIŞ (Eski oturumu kapat)
        if before.channel is not None:
            if user_id in self.active_sessions:
                start_time = self.active_sessions.pop(user_id)
                duration = (now - start_time).total_seconds()
                
                # Hangi kanaldan çıktıysa oraya yaz
                self.update_user_time(user_id, duration, before.channel.id, before.channel.name, save=False)
                
                print(f"DEBUG: Session ended for {member.display_name}. Channel: {before.channel.name}. Duration: {duration}s.")
            else:
                # Bot yeniden başladığında veya session kaybolduğunda buraya düşebilir.
                pass

        # 2. GİRİŞ (Yeni oturum başlat)
        if after.channel is not None:
            # Sadece girişte veya kanal değişiminde
            if before.channel != after.channel:
                self.active_sessions[user_id] = now
                print(f"DEBUG: Session started for {member.display_name} in {after.channel.name} at {now}.")

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
            uid = str(target.id)
            
            user_data = self.stats.get(uid, {"total_time": 0, "channels": {}})
            total_seconds = user_data["total_time"]
            
            # Eğer şu an seste ise, aktif süreyi de ekle (Hesaplamada kolaylık olsun diye genel toplama ekliyoruz)
            current_session_seconds = 0
            current_channel_id = None
            if target.id in self.active_sessions:
                current_session_seconds = (datetime.datetime.now() - self.active_sessions[target.id]).total_seconds()
                if target.voice and target.voice.channel:
                    current_channel_id = str(target.voice.channel.id)
            
            final_total = total_seconds + current_session_seconds
            formatted_total = self.format_duration(final_total)

            embed = discord.Embed(
                title=f"📊 Ses İstatistiği: {target.display_name}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="Toplam Süre", value=f"**{formatted_total}**", inline=False)
            
            # En çok vakit geçirilen kanallar (Top 5)
            channels_data = user_data.get("channels", {})
            
            # Aktif oturumu kanallara yansıt (Sadece gösterim için geçici kopya)
            if current_session_seconds > 0 and current_channel_id:
                # Mevcut veriyi kopyala ki orjinal bozulmasın
                import copy
                channels_data = copy.deepcopy(channels_data)
                
                if current_channel_id not in channels_data:
                    channels_data[current_channel_id] = {"total_time": 0, "name": target.voice.channel.name}
                
                channels_data[current_channel_id]["total_time"] += current_session_seconds

            if channels_data:
                # Sırala
                sorted_channels = sorted(
                    channels_data.items(), 
                    key=lambda item: item[1]['total_time'], 
                    reverse=True
                )
                
                top_channels_text = ""
                for i, (cid, cdata) in enumerate(sorted_channels[:5], 1):
                    c_name = cdata['name']
                    c_time = self.format_duration(cdata['total_time'])
                    top_channels_text += f"**{i}.** {c_name}: `{c_time}`\n"
                
                embed.add_field(name="En Çok Takılınan Kanallar", value=top_channels_text, inline=False)

            if current_session_seconds > 0:
                embed.set_footer(text="🟢 Şu an aktif (Süreler dahil edildi)")
                
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Stat komutunda hata: {e}")
            print(f"Stat Error: {e}")

    @commands.command(name='cüzdan', aliases=['wallet', 'coin', 'bakiye'])
    async def cuzdan(self, ctx, member: discord.Member = None):
        """Mevcut CotaSüre (bakiye) durumunu gösterir."""
        target = member or ctx.author
        uid = str(target.id)
        user_data = self.stats.get(uid, {})
        
        balance = user_data.get("balance", 0)
        total_time = user_data.get("total_time", 0)
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

        sender_uid = str(ctx.author.id)
        receiver_uid = str(recipient.id)
        
        # Gönderen kontrolü
        sender_data = self.stats.get(sender_uid, {})
        current_balance = sender_data.get("balance", 0)
        
        if current_balance < amount:
            await ctx.send(f"❌ Yetersiz bakiye. Mevcut: {current_balance} CotaSüre")
            return
            
        # Alıcı verisi oluştur (Yoksa)
        if receiver_uid not in self.stats:
            self.stats[receiver_uid] = { "total_time": 0, "balance": 0, "pending_seconds": 0, "channels": {} }
        if "balance" not in self.stats[receiver_uid]: self.stats[receiver_uid]["balance"] = 0
        
        # İşlem
        self.stats[sender_uid]["balance"] -= amount
        self.stats[receiver_uid]["balance"] += amount
        
        self.save_stats()
        
        await ctx.send(f"✅ Başarılı! **{recipient.display_name}** kullanıcısına **{amount} CotaSüre** gönderildi.\n"
                       f"📉 Yeni Bakiyen: {self.stats[sender_uid]['balance']}")

        await ctx.send(embed=embed)

    @commands.command(name='debug_sessions')
    async def debug_sessions(self, ctx):
        """(Admin) Aktif ses oturumlarını gösterir."""
        if not ctx.author.guild_permissions.administrator: return
        
        active_count = len(self.active_sessions)
        msg = f"🔍 **Aktif Oturumlar:** {active_count}\n"
        for uid, start in self.active_sessions.items():
            member = ctx.guild.get_member(uid)
            name = member.display_name if member else f"Unknown ({uid})"
            duration = (datetime.datetime.now() - start).total_seconds()
            msg += f"- {name}: {int(duration)}s\n"
            
        await ctx.send(msg)

    @commands.command(name='top10')
    async def top10(self, ctx):
        """Sunucudaki en çok ses süresine sahip 10 kişiyi gösterir."""
        if not self.stats:
            await ctx.send("Henüz kayıtlı istatistik yok.")
            return

        # Sırala (Azalan) - Yeni yapıda "total_time" alanına göre
        sorted_stats = sorted(
            self.stats.items(), 
            key=lambda item: item[1].get('total_time', 0) if isinstance(item[1], dict) else item[1], 
            reverse=True
        )
        top_list = sorted_stats[:10]

        description_lines = []
        for index, (uid, data) in enumerate(top_list, 1):
            # Yapı kontrolü
            if isinstance(data, dict):
                seconds = data.get('total_time', 0)
            else:
                seconds = data # Eski format kalıntısı varsa
            
            user = ctx.guild.get_member(int(uid))
            name = user.display_name if user else f"Kullanıcı ({uid})"
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
