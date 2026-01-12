import discord
from discord.ext import commands

class ActivityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Yoklama Al", style=discord.ButtonStyle.green, emoji="📝")
    async def yoklama_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Kullanıcı bir ses kanalında mı?
        if not interaction.user.voice:
             await interaction.response.send_message("❌ Bir ses kanalında olmalısınız!", ephemeral=True)
             return
        
        voice_channel = interaction.user.voice.channel
        members = voice_channel.members
        
        embed = discord.Embed(
            title=f"📊 Yoklama: {voice_channel.name}", 
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Talep eden: {interaction.user.display_name}")

        if not members:
            embed.description = "Ses kanalında kimse yok."
            await interaction.response.send_message(embed=embed)
            return

        # -------------------------------------------------------------
        # ⚙️ ROL AYARLARI (ANA SUNUCU İÇİN)
        # Buraya rol ID'lerinizi yazın. Örnek: 123456789012345678
        # Eğer ID 0 ise, o kategori aranmaz.
        ROLE_CONFIG = {
            "🛡️ Tank": 0,    # Örnek ID: 9876543210
            "💚 Healer": 0,  # Örnek ID: 1234567890
            "⚔️ DPS": 0,     # Örnek ID: 5555555555
            "🔮 Mage": 0     # Ekstra rol
        }
        # -------------------------------------------------------------

        # Listeleri hazırla
        classified = {key: [] for key in ROLE_CONFIG.keys()}
        others = []

        total_members = len(members)

        for member in members:
            # Yapılandırılmış rollerden birine sahip mi?
            found = False
            for role_name, role_id in ROLE_CONFIG.items():
                if role_id != 0 and member.get_role(role_id):
                    classified[role_name].append(member)
                    found = True
                    break # İlk eşleşen rolde dur
            
            # Hiçbirine uymuyorsa 'Diğer' veya varsayılan listeye ekle
            if not found:
                # Test sunucusu için: ID girilmemişse herkesi en üst rolüyle göster
                # Eğer tüm ID'ler 0 ise (Test modu)
                if all(id == 0 for id in ROLE_CONFIG.values()):
                     roles = [r for r in member.roles if r.name != "@everyone"]
                     top_role = roles[-1].mention if roles else "Rol Yok"
                     others.append(f"• {member.mention} ({top_role})")
                else:
                    # ID'ler girilmiş ama bu kişide yok
                    others.append(f"• {member.mention}")

        # Çıktıyı oluştur
        description_lines = []
        
        # 1. Özel Kategorileri Yazdır
        for role_name, member_list in classified.items():
            if member_list:
                description_lines.append(f"**{role_name} ({len(member_list)})**")
                for m in member_list:
                    description_lines.append(f"• {m.mention}")
                description_lines.append("") # Boşluk

        # 2. Diğerlerini Yazdır
        if others:
            # Eğer özel kategori varsa "Diğer" başlığı at, yoksa (test modu) direkt listele
            if any(classified.values()):
                description_lines.append(f"**Diğer ({len(others)})**")
            
            description_lines.extend(others)

        embed.description = "\n".join(description_lines)
        embed.add_field(name="Toplam Kişi", value=str(total_members), inline=False)
        
        await interaction.response.send_message(embed=embed)

class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Activity Cog hazır.')

    @commands.command(name='yoklama')
    async def yoklama(self, ctx):
        """Yoklama panelini açar."""
        embed = discord.Embed(
            title="🎯 Etkinlik Kontrol Paneli", 
            description="Ses kanalındaki katılımcıları listelemek için aşağıdaki **Yoklama Al** butonuna tıklayın.",
            color=discord.Color.dark_theme()
        )
        view = ActivityView()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Activity(bot))
