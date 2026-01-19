import discord
from discord.ext import commands
import json
import os
import datetime
import asyncio
import logging
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, COLORS

# Database import
from database.adapter import DatabaseAdapter

logger = logging.getLogger("Passive")

class PassiveRequestModal(discord.ui.Modal, title="Pasiflik Bildirimi"):
    def __init__(self, bot, channel_id):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id

    reason = discord.ui.TextInput(
        label="Mazeretiniz",
        style=discord.TextStyle.paragraph,
        placeholder="Neden aktif olamayacağınızı belirtin...",
        max_length=500
    )

    start_date = discord.ui.TextInput(
        label="Başlangıç Tarihi",
        placeholder="Örn: 01.01.2024",
        max_length=15
    )

    end_date = discord.ui.TextInput(
        label="Bitiş Tarihi",
        placeholder="Örn: 07.01.2024",
        max_length=15
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Parse dates
        try:
            start_day, start_month, start_year = map(int, self.start_date.value.split('.'))
            end_day, end_month, end_year = map(int, self.end_date.value.split('.'))
            start_date_obj = datetime.date(start_year, start_month, start_day)
            end_date_obj = datetime.date(end_year, end_month, end_day)
        except ValueError:
            await interaction.response.send_message("❌ Hatalı tarih formatı! GG.AA.YYYY formatında giriniz.", ephemeral=True)
            return
        
        # Save to database
        passive_cog = self.bot.get_cog('Passive')
        if passive_cog and hasattr(passive_cog, 'db'):
            try:
                await passive_cog.db.add_passive_request(
                    user_id=interaction.user.id,
                    user_name=interaction.user.display_name,
                    reason=self.reason.value,
                    start_date=start_date_obj,
                    end_date=end_date_obj
                )
                logger.info(f"Passive request added for {interaction.user.display_name}")
            except Exception as e:
                logger.error(f"Database error: {e}")
                await interaction.response.send_message(f"❌ Kayıt hatası: {e}", ephemeral=True)
                return

        # Notify Channel (Ephemeral) and Trigger Panel
        
        # Prepare Mentions
        mentions = ""
        for role_id in ADMIN_ROLE_IDS:
            mentions += f"<@&{role_id}> "
        
        guild_id = str(interaction.guild_id)
        await interaction.response.send_message("✅ Pasiflik bildiriminiz başarıyla kaydedildi.", ephemeral=True)
        
        # Trigger Panel Update
        passive_cog = self.bot.get_cog('Passive')
        if passive_cog:
                await passive_cog.update_passive_panel(guild_id, mentions_to_ping=mentions)
                
                # Log to System Log
                sys_log = discord.utils.get(interaction.guild.text_channels, name="cotabot-log")
                if sys_log:
                    embed = discord.Embed(
                        title="💤 Yeni Pasiflik Bildirimi",
                        description=f"**Kullanıcı:** {interaction.user.mention}\n**Sebep:** {self.reason.value}\n**Tarih:** {self.start_date.value} - {self.end_date.value}",
                        color=discord.Color(COLORS.INFO)
                    )
                    embed.set_footer(text=f"Bildirim Zamanı: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
                    await sys_log.send(embed=embed)


class PassivePanelView(discord.ui.View):
    def __init__(self, bot, channel_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id

    @discord.ui.button(label="📝 Pasiflik Bildir", style=discord.ButtonStyle.primary, custom_id="pp_open_form")
    async def open_passive_form_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PassiveRequestModal(self.bot, self.channel_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Bildirim Sil", style=discord.ButtonStyle.danger, custom_id="pp_delete_form")
    async def delete_passive_form_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check Admin
        is_admin = False
        if interaction.user.guild_permissions.administrator or interaction.user.id in ADMIN_USER_IDS:
            is_admin = True
        else:
            for r in interaction.user.roles:
                if r.id in ADMIN_ROLE_IDS: is_admin = True; break
        
        # Load from database
        passive_cog = self.bot.get_cog('Passive')
        user_requests = []
        
        if passive_cog and hasattr(passive_cog, 'db'):
            try:
                all_requests = await passive_cog.db.get_all_passive_requests()
                
                for req in all_requests:
                    show = False
                    if is_admin: show = True
                    elif req.user_id == interaction.user.id: show = True
                    
                    if show:
                        user_requests.append(req)
                        
            except Exception as e:
                logger.error(f"Database error: {e}")
                await interaction.response.send_message(f"❌ Veritabanı hatası: {e}", ephemeral=True)
                return
        
        if not user_requests:
            await interaction.response.send_message("❌ Silebileceğiniz bir bildirim bulunamadı.", ephemeral=True)
            return
            
        # Create Delete View
        view = PassiveDeleteView(self.bot, user_requests[:25])
        await interaction.response.send_message("🗑️ Silmek istediğiniz bildirimi seçin:", view=view, ephemeral=True)


class PassiveDeleteView(discord.ui.View):
    def __init__(self, bot, requests):
        super().__init__(timeout=60)
        self.bot = bot
        self.add_item(PassiveDeleteSelect(bot, requests))

class PassiveDeleteSelect(discord.ui.Select):
    def __init__(self, bot, requests):
        options = []
        for req in requests:
            # req is now a PassiveRequest model object
            req_id = str(req.id)
            u_name = req.user_name or "Bilinmiyor"
            reason = req.reason[:20] if req.reason else ""
            
            start_str = req.start_date.strftime("%d.%m.%Y")
            end_str = req.end_date.strftime("%d.%m.%Y")
            
            lbl = f"{u_name} - {reason}..."
            desc = f"Tarih: {start_str} - {end_str}"
            
            options.append(discord.SelectOption(label=lbl, description=desc, value=req_id))
            
        super().__init__(placeholder="Silinecek kaydı seçin...", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        request_id = int(self.values[0])
        deleted = False
        
        # Delete from database
        passive_cog = self.bot.get_cog('Passive')
        if passive_cog and hasattr(passive_cog, 'db'):
            try:
                deleted = await passive_cog.db.delete_passive_request(request_id)
                if deleted:
                    logger.info(f"Passive request {request_id} deleted")
            except Exception as e:
                logger.error(f"Database delete error: {e}")
                await interaction.response.send_message(f"❌ Silme hatası: {e}", ephemeral=True)
                return
            
        if deleted:
            await interaction.response.send_message("✅ Bildirim silindi.", ephemeral=True)
            # Update Panel
            passive_cog = self.bot.get_cog('Passive')
            if passive_cog:
                    await passive_cog.update_passive_panel(str(interaction.guild_id))
        else:
            await interaction.response.send_message("❌ Silme başarısız (Zaten silinmiş olabilir).", ephemeral=True)


class Passive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Database adapter
        self.db = DatabaseAdapter('sqlite:///cotabot_dev.db')
        self.db.init_db()
        logger.info("Passive cog initialized with database")

    async def check_permissions(self, ctx):
        if ctx.author.guild_permissions.administrator: return True
        if ctx.author.id in ADMIN_USER_IDS: return True
        for role in ctx.author.roles:
            if role.id in ADMIN_ROLE_IDS: return True
        await ctx.send("❌ Bu komutu kullanmak için yetkiniz yok.")
        return False

    async def update_passive_panel(self, guild_id, mentions_to_ping=None):
        """Updates the persistent passive list panel."""
        cfg_file = "passive_config.json"
        db_file = "passive_db.json"
        
        # Load Config
        channel_id = None
        message_id = None
        config_data = {}
        
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f: 
                    config_data = json.load(f)
                    guild_cfg = config_data.get(guild_id)
                    if guild_cfg: 
                        channel_id = guild_cfg.get("channel_id")
                        message_id = guild_cfg.get("message_id")
            except: pass
            
        if not channel_id: return

        # Load Requests from database
        active_requests = []
        try:
            active_requests = await self.db.get_active_passive_requests()
        except Exception as e:
            logger.error(f"Database error loading requests: {e}")

        # Create Embed
        embed = discord.Embed(title="💤 Pasiflik Listesi", description="Aşağıda mazereti geçerli olan oyuncuların listesi bulunmaktadır.", color=discord.Color(COLORS.INFO))
        embed.set_thumbnail(url="https://i.imgur.com/Z4v9s8q.png")
        
        if active_requests:
            desc_lines = []
            for req in active_requests:
                user_name = req.user_name or 'Bilinmiyor'
                reason = req.reason or '-'
                start_str = req.start_date.strftime("%d.%m.%Y")
                end_str = req.end_date.strftime("%d.%m.%Y")
                
                duration_str = ""
                try:
                    days = (req.end_date - req.start_date).days + 1
                    duration_str = f" **({days} Gün)**"
                except: pass
                
                dates = f"{start_str} - {end_str}{duration_str}"
                line = f"**{user_name}**: {reason} ({dates})"
                desc_lines.append(line)
            
            chunk_size = 1000
            user_list_str = "\n".join(desc_lines)
            if len(user_list_str) > 4000: user_list_str = user_list_str[:4000] + "..."
            
            embed.description = user_list_str
        else:
            embed.description = "Şu anda pasif durumda olan oyuncu bulunmamaktadır."

        embed.set_footer(text=f"Son Güncelleme: {datetime.datetime.now().strftime('%H:%M')}")

        channel = self.bot.get_channel(channel_id)
        if not channel: return
        
        view = PassivePanelView(self.bot, channel_id)
        
        # Ping if needed
        if mentions_to_ping:
                try:
                    ping_msg = await channel.send(f"{mentions_to_ping} Yeni pasiflik bildirimi girildi!")
                    await asyncio.sleep(5)
                    await ping_msg.delete()
                except: pass

        # Edit or Send
        if message_id:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                pass 

        msg = await channel.send(embed=embed, view=view)
        
        # Save Message ID
        config_data[guild_id]["message_id"] = msg.id
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

    @commands.command(name='pasif_panel')
    async def pasif_panel_cmd(self, ctx):
        """Pasiflik listesi panelini oluşturur/yeniler."""
        if not await self.check_permissions(ctx): return
        
        cfg_file = "passive_config.json"
        config_data = {}
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f: config_data = json.load(f)
            except: pass
        
        # Cleanup Old Message
        guild_id = str(ctx.guild.id)
        if guild_id in config_data:
                old_ch_id = config_data[guild_id].get("channel_id")
                old_msg_id = config_data[guild_id].get("message_id")
                if old_ch_id and old_msg_id:
                    try:
                        old_ch = ctx.guild.get_channel(old_ch_id)
                        if old_ch:
                            old_msg = await old_ch.fetch_message(old_msg_id)
                            await old_msg.delete()
                    except: pass
                
                if "message_id" in config_data[guild_id]: 
                    del config_data[guild_id]["message_id"]

        config_data[guild_id] = {"channel_id": ctx.channel.id}
        
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
            
        await self.update_passive_panel(str(ctx.guild.id))
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(Passive(bot))
