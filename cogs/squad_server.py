import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json
import asyncio
import datetime
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, BM_API_URL, SERVER_ID, COLORS
from .utils.chart_maker import generate_live_server_image
import logging

logger = logging.getLogger("SquadServer")

class PanelManageView(discord.ui.View):
    def __init__(self, bot, config_file):
        super().__init__(timeout=None)
        self.bot = bot
        self.config_file = config_file

    @discord.ui.button(label="Sil ve Durdur", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Yetki kontrolü
        is_admin = False
        if interaction.user.guild_permissions.administrator: is_admin = True
        elif interaction.user.id in ADMIN_USER_IDS: is_admin = True
        
        if not is_admin:
             await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
             return

        guild_id = str(interaction.guild_id)
        
        # Dosyadan oku
        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except: pass
            
        if guild_id in config:
            # Eski mesajı silmeyi dene
            ch_id = config[guild_id].get("channel_id")
            msg_id = config[guild_id].get("message_id")
            if ch_id and msg_id:
                try:
                    ch = interaction.guild.get_channel(ch_id)
                    if ch:
                        msg = await ch.fetch_message(msg_id)
                        await msg.delete()
                except: pass
            
            # Configden sil
            del config[guild_id]
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
                
            await interaction.response.send_message("✅ Panel durduruldu ve silindi.", ephemeral=True)
            
            # Reload Cog to stop loop effectively/Update state
            # Or just wait for next loop iteration which checks config
        else:
            await interaction.response.send_message("❌ Bu sunucuda aktif panel bulunamadı.", ephemeral=True)


class SquadServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.panel_config_file = "squad_panel.json"
        
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        self.live_panel_loop.start()

    def cog_unload(self):
        if self.session:
            asyncio.create_task(self.session.close())
        self.live_panel_loop.cancel()

    def get_headers(self):
        token = os.getenv("BATTLEMETRICS_TOKEN")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
    
    async def check_permissions(self, ctx):
        if ctx.author.guild_permissions.administrator: return True
        if ctx.author.id in ADMIN_USER_IDS: return True
        for role in ctx.author.roles:
            if role.id in ADMIN_ROLE_IDS: return True
        await ctx.send("❌ Bu komutu kullanmak için yetkiniz yok.")
        return False

    async def load_panel_config(self):
        if not os.path.exists(self.panel_config_file): return {}
        try:
            def _read():
                with open(self.panel_config_file, "r", encoding="utf-8") as f: return json.load(f)
            return await asyncio.to_thread(_read)
        except: return {}

    async def save_panel_config(self, data):
        def _save():
            with open(self.panel_config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        await asyncio.to_thread(_save)

    @tasks.loop(seconds=330) # 5.5 minutes
    async def live_panel_loop(self):
        await self.update_live_panels()

    @live_panel_loop.before_loop
    async def before_live_panel(self):
        await self.bot.wait_until_ready()

    async def update_live_panels(self):
        if not self.session: self.session = aiohttp.ClientSession()
        
        config = await self.load_panel_config()
        if not config: 
            return
        
        players_cog = self.bot.get_cog('SquadPlayers')
        
        # Load DB for Mapping
        player_map = {} # Name -> DiscordID or SteamID -> DiscordID
        valid_identifiers = set() # Set of valid SteamIDs and Names
        
        if os.path.exists("squad_db.json"):
            try:
                def _read_db():
                    with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
                db = await asyncio.to_thread(_read_db)
                for p in db.get("players", []):
                    valid_identifiers.add(p["steam_id"])
                    valid_identifiers.add(p["name"])
                    
                    # Map for Voice Status
                    if p.get("discord_id"):
                        player_map[p["name"]] = p["discord_id"]
                        player_map[p["steam_id"]] = p["discord_id"]
            except: pass
        
        logger.info(f"Loaded {len(player_map)} Discord ID mappings.")
            
        try:
            url = f"{BM_API_URL}/servers/{SERVER_ID}?include=player,identifier"
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status != 200: 
                    logger.error(f"BM API Error: {response.status}")
                    return
                logger.info(f"BM API Success. Status: {response.status}")
                
                data = await response.json()
                server_info = data['data']['attributes']
                included_players = data.get('included', [])
                
                # Debug types in included
                types_found = set(i.get('type') for i in included_players)
                logger.debug(f"Input Included Types: {types_found}")
                logger.debug(f"Included Count: {len(included_players)}")

                # 1. Index Identifiers (Reverse Lookup: Identifier -> Player)
                # The API structure links Identifier -> Player, not always Player -> Identifier
                player_steam_map = {} # player_id -> steamID (str)
                
                for item in included_players:
                    if item.get('type') == 'identifier':
                        attrs = item.get('attributes', {})
                        if attrs.get('type') == 'steamID':
                            steam_val = attrs.get('identifier')
                            # Check relationships for player ID
                            rels = item.get('relationships', {})
                            player_data = rels.get('player', {}).get('data')
                            if player_data and player_data.get('id'):
                                p_id = player_data.get('id')
                                player_steam_map[p_id] = steam_val

                logger.info(f"Mapped {len(player_steam_map)} SteamIDs from Identifiers.")
                
                # Process Players
                processed_list = []
                # Better Guild Selection: Use the first one from config if available
                guild = None
                if config:
                    try:
                        gid = int(list(config.keys())[0])
                        guild = self.bot.get_guild(gid)
                    except: pass
                
                if not guild and self.bot.guilds:
                    guild = self.bot.guilds[0]
                
                for p in included_players:
                    if p['type'] != 'player': continue
                    
                    if len(processed_list) == 0:
                        logger.debug(f"First Player Raw Rels: {p.get('relationships')}")

                    attrs = p['attributes']
                    p_name = attrs['name']
                    p_id = p.get('id')
                    
                    # Extract SteamID
                    steam_id = None
                    
                    # 1. Try Reverse Map (Identifiers -> Player) which we just built
                    if p_id in player_steam_map:
                        steam_id = player_steam_map[p_id]
                    
                    # 2. Try Attributes (Legacy/Some endpoints)
                    if not steam_id:
                        idents_attr = attrs.get('identifiers', [])
                        if idents_attr:
                             for ident in idents_attr:
                                 if isinstance(ident, dict) and ident.get('type') == 'steamID':
                                    steam_id = ident.get('identifier')
                                    break
                    
                    # Check DB (Filter)
                    is_valid = False
                    if steam_id and steam_id in valid_identifiers: 
                        is_valid = True
                        logger.debug(f"MATCH: {p_name} ({steam_id}) found in DB.")
                    elif p_name in valid_identifiers: 
                        is_valid = True
                        logger.debug(f"MATCH: {p_name} found by NAME in DB.")
                    
                    if not is_valid: 
                        # Strict Mode: Skip if not in DB
                        # log_debug(f"SKIP: {p_name} (Steam: {steam_id})")
                        continue

                    # Find Discord ID for Voice Check
                    d_val = player_map.get(p_name)
                    if not d_val and steam_id:
                        d_val = player_map.get(steam_id)

                    # Determine Status
                    status_text = "YOK"
                    details = "Ses Yok"
                    
                    member = None
                    if guild:
                        # Strategy 1: Try Discord ID from DB
                        if d_val:
                            # Hybrid Lookup: Int (ID) or String (Nick)
                            if isinstance(d_val, int) or (isinstance(d_val, str) and d_val.isdigit()):
                                member = guild.get_member(int(d_val))
                                if member:
                                    logger.debug(f"✅ {p_name} → Found by ID: {member.display_name}")
                                else:
                                    logger.debug(f"⚠️ {p_name} → ID {d_val} not found in guild")
                            elif isinstance(d_val, str):
                                # Try to find by display_name or name
                                d_val_lower = d_val.lower()
                                member = discord.utils.get(guild.members, display_name=d_val)
                                
                                if not member: # Try exact name
                                    member = discord.utils.get(guild.members, name=d_val)
                                    
                                if not member: # Try case-insensitive scan
                                    for m in guild.members:
                                        if m.display_name.lower() == d_val_lower or m.name.lower() == d_val_lower:
                                            member = m
                                            break
                                
                                if member:
                                    logger.debug(f"✅ {p_name} → Found by nickname: {member.display_name}")
                                else:
                                    logger.debug(f"⚠️ {p_name} → Nickname '{d_val}' not found")
                        
                        # Strategy 2: FALLBACK - Try to find member by in-game name (if DB lookup failed)
                        if not member:
                            p_name_lower = p_name.lower()
                            # Try exact match first
                            member = discord.utils.get(guild.members, display_name=p_name)
                            
                            if not member:
                                member = discord.utils.get(guild.members, name=p_name)
                            
                            # Case-insensitive / partial match as last resort
                            if not member:
                                for m in guild.members:
                                    # Check if in-game name is in Discord name or vice versa
                                    if (p_name_lower in m.display_name.lower() or 
                                        m.display_name.lower() in p_name_lower or
                                        p_name_lower in m.name.lower() or
                                        m.name.lower() in p_name_lower):
                                        member = m
                                        logger.debug(f"🔍 {p_name} → Fallback match: {m.display_name}")
                                        break
                            
                            if not member:
                                logger.debug(f"❌ {p_name} → No Discord member found (DB: {d_val})")

                    if member and member.voice and member.voice.channel:
                        status_text = "SES"
                        details = member.voice.channel.name
                        if member.voice.self_mute or member.voice.mute:
                            status_text = "MUTE"
                    else:
                        if member:
                             logger.debug(f"🔇 {p_name} → Member {member.display_name} found but NOT in voice")
                    
                    processed_list.append({
                        "name": p_name,
                        "status_text": status_text,
                        "details": details
                    })
                
                # Sort: SES first, then Name
                processed_list.sort(key=lambda x: (x["status_text"] != "SES", x["name"]))
                
                logger.info(f"Processed List Size: {len(processed_list)}")

                # Parse server info for image generation
                parsed_server_info = {
                    'name': server_info.get('name', 'Squad Server'),
                    'map': server_info.get('details', {}).get('map', '?'),
                    'players': f"{server_info.get('players', 0)}/{server_info.get('maxPlayers', 100)}",
                    'queue': str(server_info.get('details', {}).get('squad_publicQueue', 0))
                }
                
                logger.debug(f"Parsed Server Info: {parsed_server_info}")

                # Generate Image
                try:
                    image_buf = generate_live_server_image(parsed_server_info, processed_list)
                    # log_debug("Image Generated.")
                except Exception as img_err:
                    logger.error(f"Image Gen Error: {img_err}")
                    raise img_err
                
                for guild_id, cfg in config.items():
                    channel_id = cfg.get("channel_id")
                    message_id = cfg.get("message_id")
                    
                    channel = self.bot.get_channel(channel_id)
                    if not channel: continue
                    
                    image_buf.seek(0)
                    file = discord.File(image_buf, filename="status.png")
                    
                    embed = discord.Embed(color=discord.Color(COLORS.DEFAULT))
                    embed.set_image(url="attachment://status.png")
                    embed.set_footer(text=f"Son Güncelleme: {datetime.datetime.now().strftime('%H:%M:%S')}")
                    
                    # Update or Send
                    if message_id:
                        try:
                            msg = await channel.fetch_message(message_id)
                            await msg.edit(embed=embed, attachments=[file])
                        except discord.NotFound:
                             # Re-send
                             image_buf.seek(0)
                             file = discord.File(image_buf, filename="status.png")
                             new_msg = await channel.send(embed=embed, file=file)
                             config[guild_id]["message_id"] = new_msg.id
                        except Exception as e:
                            logger.error(f"Edit Error: {e}")
                    else:
                        new_msg = await channel.send(embed=embed, file=file)
                        config[guild_id]["message_id"] = new_msg.id
                    
                await self.save_panel_config(config)

        except Exception as e:
            logger.error(f"Global Update Error: {e}", exc_info=True)

    @commands.command(name='squad')
    async def squad_status(self, ctx):
        """Squad sunucusunun anlık durumunu gösterir."""
        if not self.session: self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(f"{BM_API_URL}/servers/{SERVER_ID}", headers=self.get_headers()) as response:
                if response.status != 200:
                    await ctx.send(f"❌ BattleMetrics hatası: {response.status}")
                    return
                
                data = await response.json()
                server = data['data']['attributes']
                
                name = server.get('name', 'Bilinmeyen Sunucu')
                players = server.get('players', 0)
                max_players = server.get('maxPlayers', 0)
                queue = server.get('details', {}).get('squad_publicQueue', 0)
                map_name = server.get('details', {}).get('map', 'Bilinmiyor')
                status = "🟢 Aktif" if server.get('status') == 'online' else "🔴 Kapalı"

                embed = discord.Embed(
                    title=f"🎖️ {name}",
                    description=f"**Durum:** {status}\n**Harita:** {map_name}",
                    color=discord.Color(COLORS.SQUAD)
                )
                embed.add_field(name="Oyuncular", value=f"{players}/{max_players}", inline=True)
                embed.add_field(name="Sıra", value=str(queue), inline=True)
                
                ip = server.get('ip')
                port = server.get('port')
                if ip and port:
                    embed.add_field(name="Bağlan", value=f"steam://connect/{ip}:{port}", inline=False)
                
                await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Bir hata oluştu: {e}")

    @commands.command(name='panel_kur')
    async def squad_panel(self, ctx, channel: discord.TextChannel = None):
        """Canlı sunucu istatistik panelini kurar."""
        if not await self.check_permissions(ctx): return
        
        target_channel = channel or ctx.channel
        
        status_msg = await ctx.send("🎨 **Panel oluşturuluyor, lütfen bekleyin...**")
        async with ctx.typing():
        
            config = await self.load_panel_config()
            guild_id = str(ctx.guild.id)
            
            # Cleanup old
            if guild_id in config:
                old_ch_id = config[guild_id].get("channel_id")
                old_msg_id = config[guild_id].get("message_id")
                if old_ch_id and old_msg_id:
                    try:
                        ch = ctx.guild.get_channel(old_ch_id)
                        msg = await ch.fetch_message(old_msg_id)
                        await msg.delete()
                    except: pass
            
            config[guild_id] = {"channel_id": target_channel.id}
            await self.save_panel_config(config)
            
            await status_msg.delete()
            await ctx.send(f"✅ Panel kurulumu {target_channel.mention} kanalına yapıldı. Bir sonraki döngüde (max 5dk) görünecektir.")
            # Trigger immediate update
            asyncio.create_task(self.update_live_panels())

    @commands.command(name='panel_yonet')
    async def panel_yonet(self, ctx):
        """Aktif Squad panelini gösterir ve silme seçeneği sunar."""
        if not await self.check_permissions(ctx): return

        server_id = str(ctx.guild.id)
        config = await self.load_panel_config()
        cfg = config.get(server_id)
        
        if not cfg:
            await ctx.send("❌ Bu sunucuda aktif bir panel bulunamadı.")
            return
            
        ch_id = cfg.get("channel_id")
        channel = ctx.guild.get_channel(ch_id)
        ch_mention = channel.mention if channel else "Bilinmeyen Kanal"
        
        embed = discord.Embed(title="⚙️ Panel Yönetimi", color=discord.Color(COLORS.INFO))
        embed.description = f"**Aktif Kanal:** {ch_mention}\nPanel otomatik olarak her 5 dakikada bir güncellenir."
        
        view = PanelManageView(self.bot, self.panel_config_file)
        await ctx.send(embed=embed, view=view)

    @commands.command(name='debug_voice')
    async def debug_voice(self, ctx, *, query: str):
        """Debug logic to test member lookup string/int handling."""
        if not await self.check_permissions(ctx): return

        guild = ctx.guild

        # Strip mention characters if present
        clean_query = query.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
        
        await ctx.send(f"🔍 **Debug Başlatılıyor:** `{query}` (Clean: `{clean_query}`)")

        # 1. Direct Lookup Test (Simulate logic in update_live_panels)
        member = None
        lookup_method = "?"
        
        # Exact Int Logic
        if clean_query.isdigit():
             member = guild.get_member(int(clean_query))
             lookup_method = "guild.get_member(int)"
        
        # String Logic
        if not member:
             member = discord.utils.get(guild.members, display_name=clean_query)
             lookup_method = "display_name exact"
        if not member:
             member = discord.utils.get(guild.members, name=clean_query)
             lookup_method = "name exact"
        
        if not member:
             # Case Insensitive Scan
             for m in guild.members:
                 if m.display_name.lower() == clean_query.lower() or m.name.lower() == clean_query.lower():
                     member = m
                     lookup_method = "case-insensitive scan"
                     break
        
        embed = discord.Embed(title="🕵️ Voice Debug Report", color=discord.Color(COLORS.INFO))
        embed.add_field(name="Sorgu", value=f"`{query}` (Type: {type(query).__name__})", inline=True)
        
        if member:
            embed.color = discord.Color(COLORS.SUCCESS)
            embed.add_field(name="✅ Kullanıcı Bulundu", value=f"{member.mention} (ID: `{member.id}`)", inline=False)
            embed.add_field(name="🔎 Bulma Yöntemi", value=lookup_method, inline=True)
            
            # Voice Check
            if member.voice:
                v_state = "🔊 Bağlı"
                if member.voice.channel:
                    v_state += f" ({member.voice.channel.name})"
                else:
                    v_state += " (Kanal Yok?)"
                
                if member.voice.self_mute: v_state += " [Self-Mute]"
                if member.voice.mute: v_state += " [Server-Mute]"
            else:
                v_state = "❌ Ses Yok (None)"
                
            embed.add_field(name="🎙️ Ses Durumu", value=v_state, inline=False)
            
            # DB Check
            db_match = "❌ Veritabanında Yok"
            if os.path.exists("squad_db.json"):
                try:
                    def _read_db_debug():
                        with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
                    db = await asyncio.to_thread(_read_db_debug)
                    for p in db.get("players", []):
                        # Check strict ID match or Name match
                        is_match = False
                        did = p.get("discord_id")
                        if str(did) == str(member.id): is_match = True
                        elif p["name"] == member.display_name: is_match = True
                        
                        if is_match:
                            db_match = f"✅ Var\n**Isim:** {p.get('name')}\n**SteamID:** {p.get('steam_id')}\n**Stored DID:** `{did}`"
                            break
                except: db_match = "⚠️ DB Okuma Hatası"
            
            embed.add_field(name="📂 DB Eşleşmesi", value=db_match, inline=False)
            
        else:
            embed.color = discord.Color(COLORS.ERROR)
            embed.add_field(name="❌ Sonuç", value="Kullanıcı bulunamadı.", inline=False)
            embed.add_field(name="Tavsiye", value="Cache eksik olabilir veya ID/İsim yanlış.", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SquadServer(bot))
