import discord
from discord.ext import commands
import json
import os
import datetime
import asyncio
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, COLORS

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
        # Save to DB
        db_file = "passive_db.json"
        entry = {
            "user_id": interaction.user.id,
            "user_name": interaction.user.display_name,
            "reason": self.reason.value,
            "start_date": self.start_date.value,
            "end_date": self.end_date.value,
            "timestamp": str(datetime.datetime.now())
        }
        
        data = {"requests": []}
        if os.path.exists(db_file):
            try:
                with open(db_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except: pass
            
        if "requests" not in data: data["requests"] = []
        data["requests"].append(entry)
        
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

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
        # Check if DB exists
        db_file = "passive_db.json"
        if not os.path.exists(db_file):
                await interaction.response.send_message("❌ Henüz hiç kayıt yok.", ephemeral=True)
                return

        # Load and Filter Requests
        user_requests = []
        is_admin = False
        
        # Check Admin
        if interaction.user.guild_permissions.administrator or interaction.user.id in ADMIN_USER_IDS:
            is_admin = True
        else:
                for r in interaction.user.roles:
                    if r.id in ADMIN_ROLE_IDS: is_admin = True; break
        
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
                
            today = datetime.datetime.now().date()
            
            for req in db.get("requests", []):
                    # Basic Filter for list
                    show = False
                    if is_admin: show = True
                    elif req.get("user_id") == interaction.user.id: show = True
                    
                    if show:
                        user_requests.append(req)
                        
        except: pass
        
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
            ts = req.get("timestamp", "")
            u_name = req.get("user_name", "Bilinmiyor")
            reason = req.get("reason", "")[:20]
            
            lbl = f"{u_name} - {reason}..."
            desc = f"Tarih: {req.get('start_date')} - {req.get('end_date')}"
            
            options.append(discord.SelectOption(label=lbl, description=desc, value=ts))
            
        super().__init__(placeholder="Silinecek kaydı seçin...", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        selected_ts = self.values[0]
        db_file = "passive_db.json"
        deleted = False
        
        if os.path.exists(db_file):
            try:
                with open(db_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                initial_len = len(data.get("requests", []))
                # Remove by timestamp match
                data["requests"] = [r for r in data["requests"] if r.get("timestamp") != selected_ts]
                
                if len(data["requests"]) < initial_len:
                    with open(db_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    deleted = True
            except: pass
            
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

        # Load Requests
        active_requests = []
        if os.path.exists(db_file):
            try:
                with open(db_file, "r", encoding="utf-8") as f:
                    db = json.load(f)
                    today = datetime.datetime.now().date()
                    
                    for req in db.get("requests", []):
                        # Filter Expired
                        try:
                            end_date_str = req.get("end_date", "")
                            day, month, year = map(int, end_date_str.split('.'))
                            end_date_obj = datetime.date(year, month, day)
                            
                            if end_date_obj >= today:
                                active_requests.append(req)
                        except:
                            active_requests.append(req)
            except: pass

        # Create Embed
        embed = discord.Embed(title="💤 Pasiflik Listesi", description="Aşağıda mazereti geçerli olan oyuncuların listesi bulunmaktadır.", color=discord.Color(COLORS.INFO))
        embed.set_thumbnail(url="https://i.imgur.com/Z4v9s8q.png")
        
        if active_requests:
            desc_lines = []
            for req in active_requests:
                user_name = req.get('user_name', 'Bilinmiyor')
                reason = req.get('reason', '-')
                start_str = req.get('start_date')
                end_str = req.get('end_date')
                
                duration_str = ""
                try:
                    s_d, s_m, s_y = map(int, start_str.split('.'))
                    e_d, e_m, e_y = map(int, end_str.split('.'))
                    dt_start = datetime.date(s_y, s_m, s_d)
                    dt_end = datetime.date(e_y, e_m, e_d)
                    days = (dt_end - dt_start).days + 1
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
