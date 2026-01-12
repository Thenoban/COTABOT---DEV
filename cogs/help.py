import discord
from discord.ext import commands
from .utils.config import COLORS, ADMIN_USER_IDS, ADMIN_ROLE_IDS

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_admin(self, user):
        if user.guild_permissions.administrator: return True
        if user.id in ADMIN_USER_IDS: return True
        for role in user.roles:
            if role.id in ADMIN_ROLE_IDS: return True
        return False

    @commands.command(name='help', aliases=['yardım', 'komutlar'])
    async def help_command(self, ctx):
        """Tüm komutları ve açıklamalarını detaylı olarak gösterir."""
        
        is_admin = await self.check_admin(ctx.author)
        prefix = ctx.prefix

        embed = discord.Embed(
            title="🤖 COTABOT Komut Rehberi",
            description=f"Aşağıdaki menüden komutları inceleyebilirsiniz.\nBot Prefix: `{prefix}`",
            color=discord.Color(COLORS.INFO)
        )
        
        # 🛡️ YÖNETİM KOMUTLARI (Sadece Yetkililer Görür)
        if is_admin:
            admin_desc = (
                f"`{prefix}panel_kur [kanal]` Live Squad Panel kurulumu\n"
                f"`{prefix}panel_yonet` Paneli yönet/sil\n"
                f"`{prefix}oyuncu_yonet` Oyuncu veritabanı yönetimi (Ekle/Sil/Ara)\n"
                f"`{prefix}aktiflik_panel [kanal]` Aktiflik sıralama paneli\n"
                f"`{prefix}aktiflik_yonet` Aktiflik panelini yönet\n"
                f"`{prefix}pasif_panel` Pasiflik bildirim paneli kurulumu\n"
                f"`{prefix}squad_sync` BattleMetrics <-> DB senkronizasyonu\n"
                f"`{prefix}squad_import_sheet` G-Sheets veri aktarımı\n"
                f"`{prefix}db_indir` Veritabanı yedeğini indir\n"
                f"`{prefix}debug_voice <ID>` Ses/DB eşleşme testi"
            )
            embed.add_field(name="🛡️ Yönetim (Yetkili)", value=admin_desc, inline=False)

        # 🎮 SQUAD & OYUNCU
        squad_desc = (
            f"`{prefix}squad` Sunucu anlık durumu (Oyuncu, Map, Queue)\n"
            f"`{prefix}player <isim/ID>` Oyuncu arama ve detayları\n"
            f"`{prefix}squad_top` Top 10 Oyuncu sıralaması (Puan)\n"
            f"`{prefix}squad_season` Top 10 Sezon sıralaması"
        )
        embed.add_field(name="🎮 Squad & Oyuncu", value=squad_desc, inline=False)

        # 🎤 SES & ETKİNLİK
        voice_desc = (
            f"`{prefix}stat [kullanıcı]` Ses istatistikleri ve kanal dağılımı\n"
            f"`{prefix}top10` En aktif ses kullanıcıları\n"
            f"`{prefix}duyuru` İnteraktif etkinlik oluşturma sihirbazı"
        )
        embed.add_field(name="🎤 Ses & Etkinlik", value=voice_desc, inline=False)

        # ⚙️ GENEL
        general_desc = (
            f"`{prefix}bot_durum` Sistem sağlık durumu (Sadece Yetkili)" if is_admin else ""
        )
        if general_desc:
            embed.add_field(name="⚙️ Sistem", value=general_desc, inline=False)

        embed.set_footer(text=f"Talep eden: {ctx.author.display_name} • <> Zorunlu, [] Opsiyonel", icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='yardım_detay', aliases=['detay', 'help_detay'])
    async def help_detailed_command(self, ctx):
        """Tüm komutların detaylı açıklamalarını gösterir."""
        
        is_admin = await self.check_admin(ctx.author)
        prefix = ctx.prefix
        
        embeds = []
        
        # Embed 1: Yönetim Komutları
        if is_admin:
            admin_embed = discord.Embed(
                title="🛡️ YÖNETİM KOMUTLARI",
                description="Sadece yetkililerin kullanabileceği komutlar",
                color=discord.Color(COLORS.ADMIN)
            )
            
            admin_commands = [
                (f"{prefix}panel_kur [kanal]", "Live Squad Panel kurar. Kanal belirtilmezse mevcut kanala kurar. Panel sunucu durumunu, oyuncu listesini ve haritayı canlı gösterir."),
                (f"{prefix}panel_yonet", "Kurulu paneli yönetir veya siler. İnteraktif menü sunar."),
                (f"{prefix}oyuncu_yonet", "Oyuncu veritabanını yönetir. Yeni oyuncu ekleme, mevcut oyuncu arama, silme işlemleri yapılabilir."),
                (f"{prefix}aktiflik_panel [kanal]", "Oyuncu aktiflik sıralaması paneli kurar. Son 30 günlük oynama süresine göre top 10 gösterir."),
                (f"{prefix}aktiflik_yonet", "Aktiflik panelini yeniler veya siler."),
                (f"{prefix}pasif_panel", "Pasiflik bildirim sistemi kurar. Belirlenen süre boyunca aktif olmayan oyuncuları takip eder."),
                (f"{prefix}squad_sync", "BattleMetrics API ile veritabanı senkronizasyonu yapar. Oyuncu istatistiklerini günceller."),
                (f"{prefix}squad_import_sheet", "Google Sheets'ten oyuncu verilerini veritabanına aktarır."),
                (f"{prefix}db_indir", "Tüm veritabanı dosyalarını (.json) ZIP olarak indirir. Yedekleme için kullanılır."),
                (f"{prefix}debug_voice <ID>", "Discord ID ile ses kanalı eşleşmesini test eder."),
                (f"{prefix}report <weekly|monthly> <init|view|reset>", "Performans raporu yönetimi. init: başlangıç, view: önizleme, reset: rapor yayınla ve sıfırla."),
                (f"{prefix}export_report <weekly|monthly> <excel|pdf>", "Raporu Excel veya PDF olarak export eder ve dosya olarak gönderir."),
            ]
            
            for cmd, desc in admin_commands:
                admin_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
            
            embeds.append(admin_embed)
        
        # Embed 2: Squad & Oyuncu Komutları
        squad_embed = discord.Embed(
            title="🎮 SQUAD & OYUNCU KOMUTLARI",
            description="Sunucu ve oyuncu bilgilerini görüntüleyin",
            color=discord.Color(COLORS.SUCCESS)
        )
        
        squad_commands = [
            (f"{prefix}squad", "Sunucunun anlık durumunu gösterir: Aktif oyuncular, sıra, harita, mod bilgileri. Gerçek zamanlı güncellenir."),
            (f"{prefix}player <isim|ID>", "Belirtilen oyuncuyu arar ve detaylı bilgilerini gösterir: Puan, K/D oranı, top kill, playtime, rank."),
            (f"{prefix}squad_top", "En yüksek puana sahip top 10 oyuncuyu sıralar. Genel liderboard."),
            (f"{prefix}squad_season", "Sezonluk en iyi 10 oyuncuyu gösterir. Sezon başından itibaren kazanılan puanlara göre sıralama."),
            (f"{prefix}aktiflik_panel", "Kişisel aktiflik panelini gösterir. Son 30 günlük oynama sürenizi ve sıralamanızı görüntüler."),
        ]
        
        for cmd, desc in squad_commands:
            squad_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
        
        embeds.append(squad_embed)
        
        # Embed 3: Ses & Etkinlik Komutları
        voice_embed = discord.Embed(
            title="🎤 SES & ETKİNLİK KOMUTLARI",
            description="Ses kanalı istatistikleri ve etkinlik yönetimi",
            color=discord.Color(COLORS.INFO)
        )
        
        voice_commands = [
            (f"{prefix}stat [kullanıcı]", "Ses kanalı istatistiklerini gösterir. Kullanıcı belirtilmezse kendini, belirtilirse o kişiyi gösterir. Toplam süre, kanal dağılımı, günlük ortalama."),
            (f"{prefix}top10", "En aktif ses kullanıcılarının top 10 listesi. Son 30 gün içindeki toplam ses sürelerine göre sıralama."),
            (f"{prefix}duyuru", "İnteraktif etkinlik oluşturma sihirbazı başlatır. Başlık, açıklama, tarih, katılımcı sayısı gibi bilgileri adım adım alır."),
        ]
        
        for cmd, desc in voice_commands:
            voice_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
        
        embeds.append(voice_embed)
        
        # Embed 4: Rapor & İstatistik Komutları
        report_embed = discord.Embed(
            title="📊 RAPOR & İSTATİSTİK KOMUTLARI",
            description="Performans raporları, export ve şampiyonlar (Yeni!)",
            color=discord.Color.gold()
        )
        
        report_commands = [
            (f"{prefix}hall_of_fame", "Şampiyonlar listesi (Hall of Fame). En çok haftalık/aylık şampiyonluk kazanan oyuncular ve rekorlar. Alias: !hof, !sampiyonlar"),
        ]
        
        for cmd, desc in report_commands:
            report_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
        
        embeds.append(report_embed)
        
        # Embed 5: Genel & Sistem
        if is_admin:
            system_embed = discord.Embed(
                title="⚙️ SİSTEM KOMUTLARI",
                description="Bot durumu ve sistem bilgileri",
                color=discord.Color(COLORS.WARNING)
            )
            
            system_commands = [
                (f"{prefix}bot_durum", "Bot'un sistem sağlık durumunu gösterir: CPU, RAM kullanımı, uptime, cog durumları."),
            ]
            
            for cmd, desc in system_commands:
                system_embed.add_field(name=f"`{cmd}`", value=desc, inline=False)
            
            embeds.append(system_embed)
        
        # Send embeds
        for i, embed in enumerate(embeds, 1):
            embed.set_footer(text=f"Sayfa {i}/{len(embeds)} • Talep eden: {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            if i == 1:
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
