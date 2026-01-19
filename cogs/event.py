import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio

# Database import
from database.adapter import DatabaseAdapter

# Auth Constants
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, CLAN_MEMBER_ROLE_IDS, COLORS, DEV_MODE, MANAGER_USER_IDS, MANAGER_ROLE_IDS
import logging

# Import custom exceptions
from exceptions import DiscordOperationError, DataError, JSONParseError

logger = logging.getLogger("Event")

# SocketIO broadcast for web admin panel
try:
    import sys
    from pathlib import Path
    web_admin_path = Path(__file__).parent.parent / "web_admin"
    if str(web_admin_path) not in sys.path:
        sys.path.insert(0, str(web_admin_path))
    from socketio_handler import broadcast_event
    SOCKETIO_AVAILABLE = True
    logger.info("✅ SocketIO broadcast available for web admin")
except ImportError:
    SOCKETIO_AVAILABLE = False
    broadcast_event = None
    logger.info("ℹ️ SocketIO broadcast not available (web admin may not be running)")

# Türkiye Saati (+3)
TR_TIMEZONE = datetime.timezone(datetime.timedelta(hours=3))

class EventModal(discord.ui.Modal, title="Etkinlik Oluştur"):
    def __init__(self, bot, target_channel, image_url=None, wizard_message=None):
        super().__init__()
        self.bot = bot
        self.target_channel = target_channel
        self.image_url = image_url
        self.wizard_message = wizard_message

    event_title = discord.ui.TextInput(
        label="Etkinlik Başlığı",
        placeholder="Örn: Raid Gecesi",
        max_length=100
    )

    event_time = discord.ui.TextInput(
        label="Başlangıç Zamanı (GG.AA.YYYY SS:DD)",
        placeholder="Örn: 25.01.2026 21:00",
        max_length=20
    )

    event_end_time = discord.ui.TextInput(
        label="Bitiş Zamanı (Opsiyonel)",
        placeholder="Örn: 25.01.2026 23:00",
        required=False,
        max_length=20
    )

    event_desc = discord.ui.TextInput(
        label="Açıklama",
        style=discord.TextStyle.paragraph,
        placeholder="Etkinlik detaylarını buraya yazın...",
        required=False,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Zaman formatını kontrol et
        try:
            naive_time = datetime.datetime.strptime(self.event_time.value, "%d.%m.%Y %H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Hatalı zaman formatı! Lütfen GG.AA.YYYY SS:DD formatında giriniz.", ephemeral=True)
            return

        # Zaman dilimi ayarla (Türkiye Saati)
        # Naive time'ı replace ile timezone aware yapıyoruz
        local_time = naive_time.replace(tzinfo=TR_TIMEZONE)
        
        # Bitiş zamanı kontrolü
        local_end_time = None
        if self.event_end_time.value:
            try:
                naive_end_time = datetime.datetime.strptime(self.event_end_time.value, "%d.%m.%Y %H:%M")
                local_end_time = naive_end_time.replace(tzinfo=TR_TIMEZONE)
                
                if local_end_time <= local_time:
                    await interaction.response.send_message("❌ Bitiş zamanı başlangıç zamanından sonra olmalıdır!", ephemeral=True)
                    return
            except ValueError:
                 await interaction.response.send_message("❌ Hatalı bitiş zamanı formatı!", ephemeral=True)
                 return
        
        # Timestamp oluştur
        timestamp = int(local_time.timestamp())
        time_str = f"<t:{timestamp}:F> (<t:{timestamp}:R>)"
        if local_end_time:
            time_str += f"\n**Bitiş:** <t:{int(local_end_time.timestamp())}:F>"
        
        # Kullanıcı Avatarı
        author_name = interaction.user.display_name
        author_icon = interaction.user.avatar.url if interaction.user.avatar else None

        embed = discord.Embed(
            title=f"📅 {self.event_title.value}",
            description=f"**Başlangıç:** {time_str}\n\n{self.event_desc.value}\n\nLütfen aşağıdaki butonları kullanarak katılım durumunuzu belirtiniz.",
            color=discord.Color(COLORS.SUCCESS)
        )
        embed.set_author(name=f"{author_name} Tarafından Oluşturuldu", icon_url=author_icon)
        
        embed.add_field(name="✅ Katılanlar (0)", value="-", inline=True)
        embed.add_field(name="❌ Katılmayanlar (0)", value="-", inline=True)
        embed.add_field(name="❔ Belki (0)", value="-", inline=True)

        if self.image_url:
            embed.set_image(url=self.image_url)

        # Mesaj Gönder
        view = EventView() # Persistent view
        msg = await self.target_channel.send(embed=embed, view=view)
        
        # Database'e kaydet
        cog = self.bot.get_cog("Event")
        if cog:
            guild_id = interaction.guild.id
            server_id = str(guild_id)
            
            # Get next event_id from database (not from memory!)
            # Query database for max event_id for this guild
            def get_max_event_id():
                with cog.db.session_scope() as session:
                    from database.models import Event as EventModel
                    max_id = session.query(EventModel.event_id).filter_by(
                        guild_id=guild_id
                    ).order_by(EventModel.event_id.desc()).first()
                    return max_id[0] if max_id else 0
            
            import asyncio
            max_event_id = await asyncio.to_thread(get_max_event_id)
            new_event_id = max_event_id + 1
            
            # Add event to database
            event_db_id = await cog.db.add_event(
                guild_id=guild_id,
                event_id=new_event_id,
                title=self.event_title.value,
                description=self.event_desc.value or "",
                timestamp=local_time,
                channel_id=self.target_channel.id,
                creator_id=interaction.user.id
            )
            
            # Update message_id in database
            await cog.db.update_event_message(event_db_id, msg.id)
            
            # Update embed footer
            embed.set_footer(text=f"Cotabot Event System | ID: {new_event_id}")
            await msg.edit(embed=embed)

            # Reload events from database to sync memory
            cog.events = await cog.load_events_from_db()
            
            # Log
            log_channel = discord.utils.get(interaction.guild.text_channels, name="etkinlik-log")
            if log_channel:
                 await log_channel.send(f"📢 **Yeni Etkinlik (#{new_event_id}):** {self.event_title.value} - {msg.jump_url}")

        await interaction.response.send_message(f"✅ Etkinlik başarıyla oluşturuldu! [Git]({msg.jump_url})", ephemeral=True)
        
        # Sihirbaz mesajını sil
        if self.wizard_message:
            try: await self.wizard_message.delete()
            except: pass

class EventEditModal(discord.ui.Modal, title="Etkinliği Düzenle"):
    def __init__(self, bot, message, current_title, current_time_str, current_end_time_str, current_desc):
        super().__init__()
        self.bot = bot
        self.message = message
        
        self.event_title = discord.ui.TextInput(
            label="Etkinlik Başlığı",
            default=current_title,
            max_length=100
        )
        self.event_time = discord.ui.TextInput(
            label="Başlangıç (GG.AA.YYYY SS:DD)",
            default=current_time_str,
            max_length=20
        )
        self.event_end_time = discord.ui.TextInput(
            label="Bitiş (Opsiyonel)",
            default=current_end_time_str,
            required=False,
            max_length=20
        )
        self.event_desc = discord.ui.TextInput(
            label="Açıklama",
            style=discord.TextStyle.paragraph,
            default=current_desc,
            required=False,
            max_length=1000
        )
        self.add_item(self.event_title)
        self.add_item(self.event_time)
        self.add_item(self.event_end_time)
        self.add_item(self.event_desc)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            naive_time = datetime.datetime.strptime(self.event_time.value, "%d.%m.%Y %H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Hatalı zaman formatı!", ephemeral=True)
            return

        local_time = naive_time.replace(tzinfo=TR_TIMEZONE)
        
        local_end_time = None
        if self.event_end_time.value:
            try:
                naive_end_time = datetime.datetime.strptime(self.event_end_time.value, "%d.%m.%Y %H:%M")
                local_end_time = naive_end_time.replace(tzinfo=TR_TIMEZONE)
                
                if local_end_time <= local_time:
                    await interaction.response.send_message("❌ Bitiş zamanı başlangıç zamanından sonra olmalıdır!", ephemeral=True)
                    return
            except ValueError:
                 await interaction.response.send_message("❌ Hatalı bitiş zamanı formatı!", ephemeral=True)
                 return
        
        time_str = f"<t:{int(local_time.timestamp())}:F> (<t:{int(local_time.timestamp())}:R>)"
        if local_end_time:
            time_str += f"\n**Bitiş:** <t:{int(local_end_time.timestamp())}:F>"

        embed = self.message.embeds[0]
        embed.title = f"📅 {self.event_title.value}"
        desc_text = self.event_desc.value if self.event_desc.value else ""
        embed.description = f"**Başlangıç:** {time_str}\n\n{desc_text}\n\nLütfen aşağıdaki butonları kullanarak katılım durumunuzu belirtiniz."
        
        await self.message.edit(embed=embed)
        
        cog = self.bot.get_cog("Event")
        if cog:
            # Find event in database by message_id
            guild_id = interaction.guild.id
            event_obj = await cog.db.get_event_by_message_id(guild_id, self.message.id)
            
            if event_obj:
                # Update event in database
                await cog.db.update_event(
                    event_db_id=event_obj.id,
                    title=self.event_title.value,
                    description=desc_text,
                    timestamp=local_time,
                    reminder_sent=False  # Reset reminder when editing
                )
                
                # Reload events from database to sync memory
                cog.events = await cog.load_events_from_db()
                logger.info(f"Event #{event_obj.event_id} updated in database")
        
        await interaction.response.send_message(f"✅ Etkinlik güncellendi!", ephemeral=True)
        
        log_channel = discord.utils.get(interaction.guild.text_channels, name="etkinlik-log")
        if log_channel:
             await log_channel.send(f"✏️ **Etkinlik Düzenlendi:** {self.event_title.value} - {self.message.jump_url} (Düzenleyen: {interaction.user.display_name})")

class EventWizardView(discord.ui.View):
    def __init__(self, bot, target_channel, image_url=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.target_channel = target_channel
        self.image_url = image_url
        self.author_id = None

    @discord.ui.button(label="📝 Bilgileri Gir ve Oluştur", style=discord.ButtonStyle.primary, emoji="✨")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
             await interaction.response.send_message("❌ Bu işlemi sadece komutu veren kişi yapabilir.", ephemeral=True)
             return
             
        modal = EventModal(self.bot, self.target_channel, self.image_url, interaction.message)
        await interaction.response.send_modal(modal)

class DeclineModal(discord.ui.Modal, title="Mazeret Bildir"):
    def __init__(self, view, button_interaction):
        super().__init__()
        self.view = view
        self.button_interaction = button_interaction 

    reason = discord.ui.TextInput(
        label="Neden katılamıyorsun?",
        placeholder="Örn: İşim var, Hastayım, vb.",
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.view.update_embed(interaction, "decline", reason=self.reason.value)

class EventView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def log_action(self, interaction: discord.Interaction, action: str):
        cog = interaction.client.get_cog("Event")
        if cog:
            is_active = False
            msg_id = interaction.message.id
            for events in cog.events.values():
                for event in events:
                    if event["message_id"] == msg_id:
                        is_active = True
                        break
                if is_active: break
            
            if not is_active: return

        guild = interaction.guild
        log_channel = discord.utils.get(guild.text_channels, name="etkinlik-log")
        if log_channel:
            embed = discord.Embed(
                title="📝 Etkinlik Güncellemesi",
                description=f"**Kullanıcı:** {interaction.user.mention}\n**Olay:** {action}\n**Mesaj:** [Tıkla]({interaction.message.jump_url})",
                color=discord.Color(COLORS.INFO)
            )
            embed.set_footer(text=f"Tarih: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            await log_channel.send(embed=embed)

    async def update_embed(self, interaction: discord.Interaction, status: str, reason: str = None):
        embed = interaction.message.embeds[0]
        user_mention = interaction.user.mention
        
        if len(embed.fields) < 3: return

        attendees = self.get_users_from_field(embed.fields[0].value)
        declined = self.get_users_from_field(embed.fields[1].value)
        tentative = self.get_users_from_field(embed.fields[2].value)

        attendees = [u for u in attendees if not u.startswith(user_mention)]
        declined = [u for u in declined if not u.startswith(user_mention)]
        tentative = [u for u in tentative if not u.startswith(user_mention)]

        action_text = ""
        should_log_mazeret = False

        if status == "join":
            attendees.append(user_mention)
            action_text = "✅ Katıldı"
        elif status == "decline":
            declined.append(user_mention)
            action_text = "❌ Katılmıyor"
            if reason: should_log_mazeret = True
        elif status == "maybe":
            tentative.append(user_mention)
            action_text = "❔ Belki"
            
        embed.set_field_at(0, name=f"✅ Katılanlar ({len(attendees)})", value="\n".join(attendees) if attendees else "-", inline=True)
        embed.set_field_at(1, name=f"❌ Katılmayanlar ({len(declined)})", value="\n".join(declined) if declined else "-", inline=True)
        embed.set_field_at(2, name=f"❔ Belki ({len(tentative)})", value="\n".join(tentative) if tentative else "-", inline=True)

        await interaction.response.edit_message(embed=embed)
        
        cog = interaction.client.get_cog("Event")
        if cog:
            server_id = str(interaction.guild.id)
            guild_id = interaction.guild.id
            
            # Find event in memory first
            event_dict = None
            if server_id in cog.events:
                for event in cog.events[server_id]:
                    if event["message_id"] == interaction.message.id:
                        event_dict = event
                        break
            
            # If not in memory, try database by message_id
            if not event_dict:
                event_obj = await cog.db.get_event_by_message_id(guild_id, interaction.message.id)
                if event_obj:
                    # Convert to dict format
                    event_dict = {
                        "db_id": event_obj.id,
                        "event_id": event_obj.event_id,
                        "message_id": event_obj.message_id,
                        "title": event_obj.title
                    }
            
            if event_dict:
                # Update participants in database
                user_id = interaction.user.id
                
                await cog.db.add_event_participant(
                    event_db_id=event_dict.get("db_id"),
                    user_id=user_id,
                    user_mention=user_mention,
                    status=status if status != "join" else "attendee",
                    reason=reason
                )
                
                # Reload events from database
                cog.events = await cog.load_events_from_db()
                
                # Broadcast to web admin panel for real-time updates
                if SOCKETIO_AVAILABLE and broadcast_event:
                    try:
                        broadcast_event('event_participant_update', {
                            'event_id': event_dict.get("event_id"),
                            'db_id': event_dict.get("db_id"),
                            'action': 'participant_update',
                            'user_id': str(user_id),
                            'username': interaction.user.display_name,
                            'status': status if status != "join" else "attendee",
                            'reason': reason
                        })
                        logger.info(f"📡 Broadcasted participant update for event #{event_dict.get('event_id')}")
                    except Exception as e:
                        logger.warning(f"Failed to broadcast event update to web: {e}")

        await self.log_action(interaction, action_text)

        if should_log_mazeret:
            target_name = "oyuncu-mazeret"
            mazeret_channel = discord.utils.get(interaction.guild.text_channels, name=target_name)
            
            if not mazeret_channel:
                try:
                    all_channels = await interaction.guild.fetch_channels()
                    text_channels = [c for c in all_channels if isinstance(c, discord.TextChannel)]
                    mazeret_channel = discord.utils.get(text_channels, name=target_name)
                    if not mazeret_channel:
                         for ch in text_channels:
                            if target_name in ch.name:
                                mazeret_channel = ch
                                break
                except DiscordOperationError as e:
                    logger.warning(f"Kanal fetch hatası: {e}")

            if mazeret_channel:
                try:
                    log_embed = discord.Embed(title="📝 Mazeret Bildirimi", color=discord.Color(COLORS.ERROR))
                    log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                    log_embed.add_field(name="Etkinlik", value=f"[Git]({interaction.message.jump_url})", inline=True)
                    log_embed.add_field(name="Kullanıcı", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="Mazeret", value=reason, inline=False)
                    log_embed.set_footer(text=f"Tarih: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
                    await mazeret_channel.send(embed=log_embed)
                except DiscordOperationError as e:
                    try:
                        await interaction.followup.send(f"⚠️ Mazeret loglanamadı: {e}", ephemeral=True)
                    except:
                        pass
            else:
                 try: await interaction.followup.send("⚠️ 'oyuncu-mazeret' kanalı bulunamadı.", ephemeral=True)
                 except: pass

    def get_users_from_field(self, field_value):
        if field_value == "-": return []
        return field_value.split("\n")

    @discord.ui.button(label="Varım", style=discord.ButtonStyle.green, emoji="✅", custom_id="event_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "join")
        
    @discord.ui.button(label="Yokum", style=discord.ButtonStyle.red, emoji="❌", custom_id="event_decline")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DeclineModal(self, interaction)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Belki", style=discord.ButtonStyle.secondary, emoji="❔", custom_id="event_maybe")
    async def maybe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "maybe")

    @discord.ui.button(label="Düzenle", style=discord.ButtonStyle.primary, emoji="✏️", row=1, custom_id="event_edit")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        has_permission = False
        if interaction.user.guild_permissions.administrator: has_permission = True
        elif interaction.user.id in MANAGER_USER_IDS: has_permission = True
        else:
            role_list_empty = not MANAGER_ROLE_IDS or all(id == 0 for id in MANAGER_ROLE_IDS)
            user_list_empty = not MANAGER_USER_IDS
            if role_list_empty and user_list_empty: has_permission = True
            else:
                for role in interaction.user.roles:
                    if role.id in MANAGER_ROLE_IDS:
                        has_permission = True; break
        
        cog = interaction.client.get_cog("Event")
        found_event = None
        if cog:
            server_id = str(interaction.guild.id)
            if server_id in cog.events:
                for event in cog.events[server_id]:
                    if event["message_id"] == interaction.message.id:
                        found_event = event
                        break
        
        if found_event and interaction.user.id == found_event.get("author_id"): has_permission = True
        
        if not has_permission:
            await interaction.response.send_message("Bu işlem için yetkiniz yok", ephemeral=True)
            return

        current_title = found_event.get("title", "") if found_event else ""
        current_time_str = ""
        current_end_time_str = ""  # Initialize here
        try:
            dt = datetime.datetime.fromisoformat(found_event.get("timestamp"))
            current_time_str = dt.strftime("%d.%m.%Y %H:%M")
        except: pass
        if found_event.get("end_timestamp"):
            try:
                dt_end = datetime.datetime.fromisoformat(found_event.get("end_timestamp"))
                current_end_time_str = dt_end.strftime("%d.%m.%Y %H:%M")
            except: pass

        current_desc = ""
        try:
            full_desc = interaction.message.embeds[0].description
            parts = full_desc.split("\n\n")
            if len(parts) >= 3 and "Lütfen aşağıdaki" not in parts[1]: current_desc = parts[1]
        except: pass

        modal = EventEditModal(interaction.client, interaction.message, current_title, current_time_str, current_end_time_str, current_desc)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="İptal Et", style=discord.ButtonStyle.danger, emoji="🗑️", row=1, custom_id="event_cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        has_permission = False
        if interaction.user.guild_permissions.administrator: has_permission = True
        elif interaction.user.id in ADMIN_USER_IDS: has_permission = True
        else:
            role_list_empty = not ADMIN_ROLE_IDS or all(id == 0 for id in ADMIN_ROLE_IDS)
            user_list_empty = not ADMIN_USER_IDS
            if role_list_empty and user_list_empty: has_permission = True
            else:
                for role in interaction.user.roles:
                    if role.id in ADMIN_ROLE_IDS:
                        has_permission = True; break
        
        cog = interaction.client.get_cog("Event")
        found_event = None
        guild_id = interaction.guild.id
        
        # Get event from database
        if cog:
            event_obj = await cog.db.get_event_by_message_id(guild_id, interaction.message.id)
            if event_obj:
                # Convert to dict for compatibility
                found_event = {
                    "db_id": event_obj.id,
                    "event_id": event_obj.event_id,
                    "title": event_obj.title,
                    "author_id": event_obj.creator_id
                }
        
        if found_event and interaction.user.id == found_event.get("author_id"): has_permission = True

        if not has_permission:
            await interaction.response.send_message("Bu işlem için yetkiniz yok", ephemeral=True)
            return

        # Deactivate event in database
        if found_event and cog:
            await cog.db.deactivate_event(found_event["db_id"])
            # Reload events from database to sync memory
            cog.events = await cog.load_events_from_db()
            logger.info(f"Event #{found_event['event_id']} deactivated in database")
        
        event_title = found_event.get("title", "Bilinmeyen Etkinlik") if found_event else "Bilinmeyen Etkinlik"
        
        # Send response BEFORE attempting to delete message
        await interaction.response.send_message(f"✅ **{event_title}** etkinliği iptal edildi.", ephemeral=True)
        
        # Log to channel
        log_channel = discord.utils.get(interaction.guild.text_channels, name="etkinlik-log")
        if log_channel:
             await log_channel.send(f"🗑️ **Etkinlik İptal Edildi:** {event_title} (Silen: {interaction.user.display_name})")

        # Try to delete message (after response sent)
        try:
            await interaction.message.delete()
        except DiscordOperationError as e:
            # Message deletion failed, but event is already deactivated
            logger.warning(f"Could not delete event message: {e}")

    @discord.ui.button(label="Yoklama Al", style=discord.ButtonStyle.gray, emoji="📋", row=1, custom_id="event_attendance")
    async def attendance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        has_permission = False
        if interaction.user.guild_permissions.administrator: has_permission = True
        elif interaction.user.id in ADMIN_USER_IDS: has_permission = True
        else:
            role_list_empty = not ADMIN_ROLE_IDS or all(id == 0 for id in ADMIN_ROLE_IDS)
            user_list_empty = not ADMIN_USER_IDS
            if role_list_empty and user_list_empty: has_permission = True
            else:
                for role in interaction.user.roles:
                    if role.id in ADMIN_ROLE_IDS:
                        has_permission = True; break
        
        if not has_permission:
             await interaction.response.send_message("Bu işlem için yetkiniz yok", ephemeral=True)
             return

        if not interaction.user.voice:
             await interaction.response.send_message("❌ Önce bir ses kanalına katılmalısınız!", ephemeral=True)
             return
        
        voice_channel = interaction.user.voice.channel
        vc_members = {m.mention for m in voice_channel.members if not m.bot}
        
        embed = interaction.message.embeds[0]
        attendees_text = embed.fields[0].value
        if attendees_text == "-": signed_users = set()
        else: signed_users = set(attendees_text.split("\n"))

        present_and_signed = vc_members.intersection(signed_users)
        present_unsigned = vc_members.difference(signed_users)
        absent_signed = signed_users.difference(vc_members)
        
        report_embed = discord.Embed(
            title=f"📋 Yoklama Raporu: {embed.title.replace('📅 ', '')}", 
            description=f"**Ses Kanalı:** {voice_channel.mention}\n**Tarih:** <t:{int(datetime.datetime.now().timestamp())}:F>",
            color=discord.Color(COLORS.INFO)
        )
        def format_list(s): return "\n".join(s) if s else "-"
        report_embed.add_field(name=f"✅ Eksiksizler ({len(present_and_signed)})", value=format_list(present_and_signed), inline=False)
        report_embed.add_field(name=f"⚠️ Davetsizler ({len(present_unsigned)})", value=format_list(present_unsigned), inline=False)
        report_embed.add_field(name=f"❌ Kaçaklar ({len(absent_signed)})", value=format_list(absent_signed), inline=False)
        await interaction.response.send_message(embed=report_embed, ephemeral=True)

    @discord.ui.button(label="Tik Yok", style=discord.ButtonStyle.secondary, emoji="📢", row=1, custom_id="event_tikyok")
    async def tikyok_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        has_permission = False
        if interaction.user.guild_permissions.administrator: has_permission = True
        elif interaction.user.id in ADMIN_USER_IDS: has_permission = True
        else:
            role_list_empty = not ADMIN_ROLE_IDS or all(id == 0 for id in ADMIN_ROLE_IDS)
            user_list_empty = not ADMIN_USER_IDS
            if role_list_empty and user_list_empty: has_permission = True
            else:
                for role in interaction.user.roles:
                    if role.id in ADMIN_ROLE_IDS:
                        has_permission = True; break
        
        if not has_permission:
            # Also allow managers (unlike other admin actions, tikyok might be useful for managers too)
            # Checking manager permissions
            is_manager = interaction.user.id in MANAGER_USER_IDS
            if not is_manager and MANAGER_ROLE_IDS:
                for role in interaction.user.roles:
                    if role.id in MANAGER_ROLE_IDS:
                        is_manager = True; break
            
            if not is_manager:
                await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
                return

        # TikYok Logic
        embed = interaction.message.embeds[0]
        all_reactors = []
        def extract_mentions(field_val):
            if field_val == "-": return []
            return field_val.split("\n")

        for i in range(3):
            if len(embed.fields) > i:
                users = extract_mentions(embed.fields[i].value)
                all_reactors.extend(users)
        
        reacted_set = set(all_reactors)
        target_members = set()
        group_name = "Klan Üyeleri (Varsayılan)"
        
        # Default to Clan Roles
        found_roles = 0
        for r_id in CLAN_MEMBER_ROLE_IDS:
            r_obj = interaction.guild.get_role(r_id)
            if r_obj:
                target_members.update(r_obj.members)
                found_roles += 1
        
        if found_roles == 0:
            await interaction.response.send_message("⚠️ Varsayılan roller (CLAN_MEMBER_ROLE_IDS) sunucuda bulunamadı veya yapılandırılmadı.", ephemeral=True)
            return

        missing_members = []
        for member in target_members:
            if member.bot: continue
            if member.mention not in reacted_set:
                missing_members.append(member)

        if not missing_members:
            await interaction.response.send_message(f"✅ **{group_name}** grubundaki herkes tepki vermiş!", ephemeral=True)
        else:
            missing_list = "\n".join([m.mention for m in missing_members])
            result_embed = discord.Embed(
                title=f"⚠️ {group_name} - Tepki Vermeyenler ({len(missing_members)})",
                description=missing_list if len(missing_list) < 4000 else "Liste çok uzun...",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=result_embed, ephemeral=True)


class EventManageActionsView(discord.ui.View):
    def __init__(self, bot, message, event_data):
        super().__init__(timeout=180)
        self.bot = bot
        self.message = message
        self.event_data = event_data

    async def check_permissions(self, interaction):
        if interaction.user.guild_permissions.administrator: return True
        if interaction.user.id in ADMIN_USER_IDS: return True
        if interaction.user.id == self.event_data.get("author_id"): return True
        for role in interaction.user.roles:
            if role.id in ADMIN_ROLE_IDS: return True
        return False

    @discord.ui.button(label="Düzenle", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
            return

        current_title = self.event_data.get("title", "")
        current_time_str = ""
        try:
            dt = datetime.datetime.fromisoformat(self.event_data.get("timestamp"))
            current_time_str = dt.strftime("%d.%m.%Y %H:%M")
        except: pass
        
        current_end_time_str = ""
        if self.event_data.get("end_timestamp"):
            try:
                dt_end = datetime.datetime.fromisoformat(self.event_data.get("end_timestamp"))
                current_end_time_str = dt_end.strftime("%d.%m.%Y %H:%M")
            except: pass

        current_desc = ""
        try:
            full_desc = self.message.embeds[0].description
            parts = full_desc.split("\n\n")
            if len(parts) >= 3 and "Lütfen aşağıdaki" not in parts[1]: current_desc = parts[1]
        except: pass

        modal = EventEditModal(self.bot, self.message, current_title, current_time_str, current_end_time_str, current_desc)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Kapat / Sil", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
            return

        cog = self.bot.get_cog("Event")
        if cog:
            guild_id = interaction.guild.id
            # Get event from database by message_id
            event_obj = await cog.db.get_event_by_message_id(guild_id, self.message.id)
            
            if event_obj:
                # Archive event first (convert to dict format for archive function)
                event_dict = {
                    "db_id": event_obj.id,
                    "event_id": event_obj.event_id,
                    "title": event_obj.title,
                    "attendees": [],
                    "declined": [],
                    "tentative": []
                }
                
                # Load participants into dict format
                if event_obj.participants:
                    for p in event_obj.participants:
                        if p.status == "attendee":
                            event_dict["attendees"].append(p.user_mention)
                        elif p.status == "declined":
                            event_dict["declined"].append(p.user_mention)
                        elif p.status == "tentative":
                            event_dict["tentative"].append(p.user_mention)
                
                await cog.archive_event(event_dict, interaction.guild)
                
                # Deactivate event in database
                await cog.db.deactivate_event(event_obj.id)
                # Reload events from database to sync memory
                cog.events = await cog.load_events_from_db()
                logger.info(f"Event #{event_obj.event_id} archived and deactivated")
        
        log_channel = discord.utils.get(interaction.guild.text_channels, name="etkinlik-log")
        if log_channel:
             event_title = self.event_data.get('title', 'Bilinmeyen')
             await log_channel.send(f"🗑️ **Etkinlik Kapatıldı/Arşivlendi:** {event_title} (Yöneten: {interaction.user.display_name})")

        try:
            await self.message.delete()
            await interaction.response.send_message("✅ Etkinlik kapatıldı ve arşivlendi.", ephemeral=True)
        except:
             await interaction.response.send_message("⚠️ Etkinlik veritabanından silindi/arşivlendi ancak mesaj silinemedi.", ephemeral=True)


class EventSelect(discord.ui.Select):
    def __init__(self, events):
        options = []
        seen_values = set()
        for idx, event in enumerate(events[:25]):
            e_id = event.get("event_id", "?")
            dt_str = event.get("timestamp", "").split("T")[0]
            label = f"#{e_id} {event['title']}"[:100]
            
            # Ensure unique value - use event_id if valid, otherwise use index
            if event.get("event_id") is not None and str(event["event_id"]) not in seen_values:
                value = str(event["event_id"])
            else:
                # Fallback to using index if event_id is missing or duplicate
                value = f"idx_{idx}_{event.get('message_id', idx)}"
            
            seen_values.add(value)
            options.append(discord.SelectOption(label=label, description=f"Tarih: {dt_str}", value=value))
            logger.debug(f"Added event option: label='{label}', value='{value}'")

        # Log all values to check for duplicates at Discord API level
        all_values = [opt.value for opt in options]
        logger.info(f"EventSelect: Creating select with {len(options)} options, values: {all_values}")
        if len(all_values) != len(set(all_values)):
            logger.error(f"DUPLICATE VALUES IN OPTIONS: {all_values}")

        super().__init__(
            placeholder="Yönetmek için bir etkinlik seçin...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="event_select_menu"
        )


    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        cog = interaction.client.get_cog("Event")
        target_event = None
        
        if cog:
            server_id = str(interaction.guild.id)
            if server_id in cog.events:
                # Check if value is an event_id (numeric) or index-based (starts with "idx_")
                if selected_value.startswith("idx_"):
                    # Extract index from "idx_{idx}_{message_id}"
                    parts = selected_value.split("_")
                    try:
                        idx = int(parts[1])
                        if idx < len(cog.events[server_id]):
                            target_event = cog.events[server_id][idx]
                    except (IndexError, ValueError):
                        pass
                else:
                    # Try to find by event_id
                    try:
                        event_id = int(selected_value)
                        for e in cog.events[server_id]:
                            if e.get("event_id") == event_id:
                                target_event = e
                                break
                    except ValueError:
                        pass
        
        if not target_event:
            await interaction.response.send_message("❌ Etkinlik bulunamadı.", ephemeral=True)
            return

        try:
            channel = interaction.guild.get_channel(target_event["channel_id"])
            if not channel: channel = await interaction.guild.fetch_channel(target_event["channel_id"])
            msg = await channel.fetch_message(target_event["message_id"])
        except:
            await interaction.response.send_message("❌ Etkinlik mesajına erişilemedi (silinmiş olabilir).", ephemeral=True)
            return

        manage_view = EventManageActionsView(interaction.client, msg, target_event)
        await interaction.response.send_message(f"Seçilen Etkinlik: **{target_event['title']}**\nNe yapmak istersiniz?", view=manage_view, ephemeral=True)


class EventListView(discord.ui.View):
    def __init__(self, bot, events):
        super().__init__()
        self.add_item(EventSelect(events))


class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseAdapter('sqlite:///cotabot_dev.db')
        # Initialize db tables
        self.db.init_db()
        # Keep events dict for backward compatibility with views
        self.events = {}
        self.history = {}
        
    async def cog_load(self):
        # Load events from database instead of JSON
        self.events = await self.load_events_from_db()
        self.history = {}  # History not loaded in memory anymore
        self.check_events_task.start()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_events_task.cancel()
        self.check_reminders.cancel()

    async def load_events_from_db(self):
        """Load all active events from database and organize by guild_id"""
        try:
            # Get all guilds that bot is in
            events_dict = {}
            for guild in self.bot.guilds:
                guild_id_str = str(guild.id)
                active_events = await self.db.get_active_events(guild.id)
                
                if active_events:
                    events_list = []
                    for event in active_events:
                        # Convert database event to dict format for compatibility
                        event_dict = {
                            "db_id": event.id,  # ADD THIS - database primary key
                            "event_id": event.event_id,
                            "message_id": event.message_id,
                            "channel_id": event.channel_id,
                            "author_id": event.creator_id,
                            "title": event.title,
                            "timestamp": event.timestamp.isoformat() if event.timestamp else "",
                            "description": event.description or "",
                            "attendees": [],
                            "declined": [],
                            "tentative": [],
                            "reminder_sent": event.reminder_sent,
                            "active": event.active
                        }
                        
                        # Load participants
                        if event.participants:
                            for p in event.participants:
                                if p.status == "attendee":
                                    event_dict["attendees"].append(p.user_mention)
                                elif p.status == "declined":
                                    event_dict["declined"].append(p.user_mention)
                                elif p.status == "tentative":
                                    event_dict["tentative"].append(p.user_mention)
                        
                        events_list.append(event_dict)
                    
                    events_dict[guild_id_str] = events_list
                    logger.info(f"Loaded {len(events_list)} events for guild {guild_id_str}")
            
            return events_dict
        except Exception as e:
            logger.error(f"Error loading events from database: {e}", exc_info=True)
            return {}



    async def archive_event(self, event, guild):
        """Archive event - Database already marks event as inactive"""
        server_id = str(guild.id)
        attendees = event.get("attendees", [])
        declined = event.get("declined", [])
        tentative = event.get("tentative", [])
        all_interacted = set()
        def extract_mention(text): return text.split(" ")[0]
        for u in attendees: all_interacted.add(extract_mention(u))
        for u in declined: all_interacted.add(extract_mention(u))
        for u in tentative: all_interacted.add(extract_mention(u))
        
        missing_members = []
        target_role_members = set()
        for r_id in CLAN_MEMBER_ROLE_IDS:
            role = guild.get_role(r_id)
            if role:
                for member in role.members:
                    if not member.bot:
                        target_role_members.add(member)
        
        for member in target_role_members:
            if member.mention not in all_interacted:
                missing_members.append(member.mention)
        
        # Log archive stats
        logger.info(
            f"Event '{event.get('title')}' archived: "
            f"{len(attendees)} attended, {len(declined)} declined, "
            f"{len(tentative)} tentative, {len(missing_members)} missing"
        )
        
        # Database already has the event marked as inactive (active=False)
        # No need to write to JSON history file anymore

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        """Her dakika etkinlikleri kontrol eder ve 15 dk kala hatırlatma gönderir."""
        now = datetime.datetime.now(TR_TIMEZONE)
        data_changed = False

        for server_id, events_list in self.events.items():
            for event in events_list:
                # Daha önce hatırlatma gönderildi mi veya etkinlik pasif mi?
                if event.get("reminder_sent", False) or not event.get("active", True):
                    continue

                try:
                    event_time = datetime.datetime.fromisoformat(event["timestamp"]).replace(tzinfo=TR_TIMEZONE)
                except ValueError:
                    continue  # Tarih formatı bozuksa atla

                # Zaman farkını hesapla
                diff = event_time - now
                
                # 15 dakika kala (14-16 dk arası tolerans) ve etkinlik henüz başlamadıysa
                if datetime.timedelta(minutes=14) <= diff <= datetime.timedelta(minutes=16):
                    
                    guild = self.bot.get_guild(int(server_id))
                    if not guild: continue

                    # 1. Genel Kanal Bildirimi
                    channel_id = event.get("channel_id")
                    channel = guild.get_channel(channel_id)
                    
                    if channel:
                        try:
                            msg_link = f"https://discord.com/channels/{server_id}/{channel_id}/{event['message_id']}"
                            # Katılımcı rolünü etiketleyelim (eğer varsa configden çekilebilir ama şimdilik genel)
                            # Daha spesifik: Katılımcıları etiketle? Çok spam olabilir.
                            # Embed ile şık bir hatırlatma
                            embed = discord.Embed(
                                title="⏰ Etkinlik Hatırlatıcı",
                                description=f"**{event['title']}** etkinliği yaklaşık **15 dakika** sonra başlayacak!\n\n[Etkinliğe Git]({msg_link})",
                                color=discord.Color(COLORS.WARNING)
                            )
                            await channel.send(content="@here", embed=embed)
                        except Exception as e:
                            logger.error(f"Reminder Channel Error: {e}")

                    # 2. Katılımcılara DM
                    attendees = event.get("attendees", [])
                    
                    # DM gönderilecek kullanıcıları bul
                    # attendees listesinde mention stringleri var ("<@123>" veya "Display Name")
                    # Discord ID'yi mentiondan parse etmeliyiz
                    
                    for att in attendees:
                        user_id = None
                        if att.startswith("<@") and att.endswith(">"):
                            try:
                                user_id = int(att[2:-1].replace("!", ""))
                            except: pass
                        
                        # Eğer ID bulamadıysak, metin tabanlı isim olabilir (Eski veri), DM atamayız.
                        if user_id:
                            member = guild.get_member(user_id)
                            if member:
                                try:
                                    dm_embed = discord.Embed(
                                        title=f"🔔 Hatırlatma: {event['title']}",
                                        description=f"Etkinlik 15 dakika içinde başlıyor! Hazırlanın.\n\nZaman: <t:{int(event_time.timestamp())}:R>",
                                        color=discord.Color(COLORS.INFO)
                                    )
                                    await member.send(embed=dm_embed)
                                except discord.Forbidden:
                                    pass # DM kapalı
                                except Exception as e:
                                    logger.error(f"DM Error ({member.display_name}): {e}")

                    # 3. Update reminder status in database
                    event_db_id = event.get("db_id")
                    if event_db_id:
                        await self.db.update_reminder_status(event_db_id, True)
                        logger.info(f"Reminder sent for event #{event.get('event_id')}")
                        data_changed = True
        
        if data_changed:
            # Reload events from database to sync memory
            self.events = await self.load_events_from_db()

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(EventView())
        logger.info('Event Cog ready and View loaded.')

    @commands.command(name='etkinlikler', aliases=['events'])
    async def list_events(self, ctx):
        try:
            # Fetch events from DB (Active + Archived, limit 25)
            # Use get_all_events
            events_obj = await self.db.get_all_events(ctx.guild.id, limit=25)
            
            if not events_obj:
                await ctx.send("📭 Kayıtlı etkinlik bulunmuyor.")
                return

            events_list = []
            for event in events_obj:
                # Convert database event to dict format for compatibility
                event_dict = {
                    "db_id": event.id,
                    "event_id": event.event_id,
                    "message_id": event.message_id,
                    "channel_id": event.channel_id,
                    "author_id": event.creator_id,
                    "title": event.title,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else "",
                    "description": event.description or "",
                    "attendees": [],
                    "declined": [],
                    "tentative": [],
                    "reminder_sent": event.reminder_sent,
                    "active": event.active
                }
                
                if event.participants:
                    for p in event.participants:
                        if p.status == "attendee": event_dict["attendees"].append(p.user_mention)
                        elif p.status == "declined": event_dict["declined"].append(p.user_mention)
                        elif p.status == "tentative": event_dict["tentative"].append(p.user_mention)
                
                events_list.append(event_dict)
            
            embed = discord.Embed(title="📅 Etkinlik Listesi (Son 25)", color=discord.Color(COLORS.INFO))
            desc = ""
            for event in events_list:
                dt_str = "Bilinmiyor"
                try:
                    dt = datetime.datetime.fromisoformat(event["timestamp"])
                    dt_str = dt.strftime("%d.%m.%Y %H:%M")
                except: pass
                
                e_id = event.get("event_id", "?")
                status = "🟢" if event.get("active") else "🔴"
                msg_link = f"https://discord.com/channels/{ctx.guild.id}/{event['channel_id']}/{event['message_id']}"
                
                line = f"{status} **#{e_id}** - [{event['title']}]({msg_link}) (`{dt_str}`)\n"
                if len(desc) + len(line) > 4000:
                    desc += "...ve daha fazlası"
                    break
                desc += line
                
            embed.description = desc
            embed.set_footer(text="🟢 Aktif | 🔴 Arşivlenmiş/Pasif")
            
            # Use View with Select Menu to manage ANY event in the list
            view = EventListView(self.bot, events_list)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            await ctx.send(f"❌ Komut çalıştırılırken hata: {e}")
            logger.error(f"List events error: {e}", exc_info=True)


    # !etkinlik command removed (deprecated)

    @commands.command(name='duyuru', aliases=['duyurub'])
    async def duyuru(self, ctx, channel: discord.TextChannel = None):
        target_channel = channel or ctx.channel
        image_url = None
        if ctx.message.attachments: image_url = ctx.message.attachments[0].url
            
        view = EventWizardView(self.bot, target_channel, image_url)
        view.author_id = ctx.author.id
        
        embed = discord.Embed(
            title="✨ Etkinlik Oluşturucu",
            description=f"Hedef Kanal: {target_channel.mention}\n\nEtkinlik bilgilerini girmek için aşağıdaki butona tıklayın.",
            color=discord.Color(COLORS.INFO)
        )
        if image_url: embed.set_thumbnail(url=image_url)
        await ctx.send(embed=embed, view=view)

    # !tikyok command removed (moved to EventView button)

    @tasks.loop(hours=1)
    async def check_events_task(self):
        """Saatlik kontrol: Geçmiş etkinlikleri arşivle. Deprecated in favor of check_reminders."""
        data_changed = False
        now = datetime.datetime.now(TR_TIMEZONE)
        
        for server_id, events in list(self.events.items()):
            for event in list(events):
                try:
                    # Check if event has started and archive it
                    event_time = datetime.datetime.fromisoformat(event["timestamp"]).replace(tzinfo=TR_TIMEZONE)
                    
                    if now >= event_time:
                        try:
                            guild_id = int(server_id)
                            channel = self.bot.get_channel(event["channel_id"])
                            if channel:
                                await self.archive_event(event, channel.guild)
                                
                                # Deactivate in database
                                event_db_id = event.get("db_id")
                                if event_db_id:
                                    await self.db.deactivate_event(event_db_id)
                                    logger.info(f"Event #{event.get('event_id')} started and archived")
                                    data_changed = True
                                
                                # Optional: Send notification
                                try:
                                    msg = await channel.fetch_message(event["message_id"])
                                    embed = msg.embeds[0]
                                    attendees_field = embed.fields[0].value if embed.fields else "-"
                                    if attendees_field != "-":
                                        await channel.send(f"⏰ **{event['title']}** etkinliği başlıyor!\n{attendees_field}")
                                    else:
                                        await channel.send(f"⏰ **{event['title']}** etkinliği başlıyor! (Katılan kimse görünmüyor)")
                                    
                                    log_channel = discord.utils.get(channel.guild.text_channels, name="etkinlik-log")
                                    if log_channel:
                                        await log_channel.send(f"🏁 **Etkinlik Başladı ve Arşivlendi:** {event['title']}")
                                except discord.NotFound:
                                    logger.warning(f"Event message not found for event #{event.get('event_id')}")
                                except Exception as e:
                                    logger.error(f"Error notifying event start: {e}")
                        except Exception as e:
                            logger.error(f"Event archive error: {e}")
                            
                except Exception as e:
                    logger.error(f"Event processing error: {e}")

        if data_changed:
            # Reload events from database to sync memory
            self.events = await self.load_events_from_db()

    @check_events_task.before_loop
    async def before_check_events(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Event(bot))
