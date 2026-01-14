"""
Squad Players - UI Modals
Oyuncu ekleme, arama ve düzenleme için modal dialoglar
"""
import discord
import os
import datetime
import json
import asyncio
import logging

# Import custom exceptions
from exceptions import DatabaseError, ValidationError, InvalidSteamIDError

logger = logging.getLogger("SquadPlayers.Modals")


class PlayerAddModal(discord.ui.Modal, title="Oyuncu Ekle / Güncelle"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    steam_id = discord.ui.TextInput(
        label="Steam ID (64)",
        placeholder="76561198...",
        min_length=17,
        max_length=17
    )

    player_name = discord.ui.TextInput(
        label="Oyuncu İsmi",
        placeholder="Oyun içi tam isim",
        max_length=50
    )

    discord_id = discord.ui.TextInput(
        label="Discord ID (Opsiyonel)",
        placeholder="Sadece ID giriniz (Örn: 3050...)",
        required=False,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        s_id = self.steam_id.value
        p_name = self.player_name.value
        d_id = self.discord_id.value

        if not s_id.isdigit():
            await interaction.response.send_message("❌ Steam ID sadece rakamlardan oluşmalıdır.", ephemeral=True)
            return

        db_file = "squad_db.json"
        data = {"players": []}
        if os.path.exists(db_file):
            try:
                def _read():
                    with open(db_file, "r", encoding="utf-8") as f: 
                        return json.load(f)
                data = await asyncio.to_thread(_read)
            except:
                pass

        found = False
        # Discord ID can be numeric ID or username string
        parsed_d_id = None
        if d_id:
            if d_id.isdigit():
                parsed_d_id = int(d_id)  # Numeric Discord ID
            else:
                parsed_d_id = d_id  # Discord username (string)

        for p in data.get("players", []):
            if p["steam_id"] == s_id:
                p["name"] = p_name
                if parsed_d_id: 
                    p["discord_id"] = parsed_d_id
                found = True
                break
        
        if not found:
            new_p = {
                "steam_id": s_id,
                "name": p_name,
                "discord_id": parsed_d_id,
                "stats": {}, 
                "season_stats": {}
            }
            if "players" not in data: 
                data["players"] = []
            data["players"].append(new_p)

        log_msg = f"[{datetime.datetime.now()}] Manual Player Update: {p_name} ({s_id}) by {interaction.user}"
        try:
            with open("squad_debug.log", "a", encoding="utf-8") as f: 
                f.write(log_msg + "\n")
        except: 
            pass

        # HYBRID MODE: Check database FIRST to determine correct action
        cog = self.bot.get_cog("SquadPlayers")
        player_exists_in_db = False
        
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            try:
                existing_player = await cog.db.get_player_by_steam_id(s_id)
                player_exists_in_db = bool(existing_player)
            except:
                pass
        
        # Determine action based on database check (SQLite) or JSON (fallback)
        if cog and hasattr(cog, 'json_mode') and not cog.json_mode:
            action = "GÜNCELLENDİ" if player_exists_in_db else "EKLENDİ"
        else:
            action = "GÜNCELLENDİ" if found else "EKLENDİ"
        
        # CRITICAL: Respond to interaction FIRST (before slow sync)
        await interaction.response.send_message(
            f"✅ Oyuncu başarıyla **{action}**!\nİsim: {p_name}\nSteamID: {s_id}", 
            ephemeral=True
        )
        
        # HYBRID MODE: Save to database
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode - save to database instead of JSON
            try:
                if player_exists_in_db:
                    await cog.db.update_player(s_id, name=p_name, discord_id=parsed_d_id)
                else:
                    await cog.db.add_player(s_id, p_name, parsed_d_id)
                
                # Log to channel
                await cog.log_to_channel(
                    interaction.guild, 
                    "✏️ Oyuncu (DB)", 
                    f"**Oyuncu:** {p_name}\n**SteamID:** `{s_id}`\n**Discord:** {parsed_d_id or '-'}", 
                    interaction.user
                )
                return  # Exit - database handled it
            except DatabaseError as e:
                logger.error(f"DB save error: {e}, fallback to JSON", exc_info=True)
        
        # Now do slow operations in background
        cog = self.bot.get_cog("SquadPlayers")
        if cog:
            # Save to DB and auto-sync to Sheets (async background task)
            asyncio.create_task(cog._save_db_and_sync(data))
            
            # Log to Channel
            await cog.log_to_channel(
                interaction.guild, 
                "✏️ Oyuncu Düzenlendi/Eklendi", 
                f"**Oyuncu:** {p_name}\n**SteamID:** `{s_id}`\n**Discord:** {parsed_d_id or '-'}", 
                interaction.user
            )
        else:
            # Fallback if cog not found (shouldn't happen)
            data["last_update"] = str(datetime.datetime.now())
            def _save():
                with open(db_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            await asyncio.to_thread(_save)


class PlayerSearchModal(discord.ui.Modal, title="Oyuncu Ara"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    name_query = discord.ui.TextInput(
        label="Oyuncu İsmi",
        placeholder="Aramak istediğiniz ismin bir kısmını yazın...",
        min_length=2,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        query = self.name_query.value.lower()
        
        # HYBRID MODE: Search in database or JSON
        cog = self.bot.get_cog("SquadPlayers")
        matches = []
        
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode
            try:
                all_players = await cog.db.get_all_players()
                matches = [{
                    "steam_id": p.steam_id,
                    "name": p.name,
                    "discord_id": p.discord_id
                } for p in all_players if query in p.name.lower()]
            except DatabaseError as e:
                logger.error(f"DB search error: {e}", exc_info=True)
        
        # JSON fallback
        if not matches and os.path.exists("squad_db.json"):
            try:
                def _read_search():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return [p for p in data.get("players", []) if query in p["name"].lower()]
                matches = await asyncio.to_thread(_read_search)
            except: 
                pass
        
        if not matches:
            await interaction.response.send_message("❌ Eşleşen oyuncu bulunamadı.", ephemeral=True)
            return
            
        matches.sort(key=lambda x: x["name"])
        
        # Import PlayerSelectView from views module
        from .views import PlayerSelectView
        
        view = PlayerSelectView(self.bot, matches[:25])
        await interaction.response.send_message(
            f"🔍 **'{query}'** için {len(matches)} sonuç bulundu. İşlem yapmak için seçiniz:", 
            view=view, 
            ephemeral=True
        )
