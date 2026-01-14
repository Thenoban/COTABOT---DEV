"""
Squad Players - Google Sheets Integration
Oyuncu veritabanını Google Sheets ile senkronize eder
"""
import asyncio
import logging
import traceback
import datetime

# Import custom exceptions
from exceptions import GoogleSheetsAPIError, APIError

logger = logging.getLogger("SquadPlayers.SheetsSync")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    gspread = None
    Credentials = None
    GSPREAD_AVAILABLE = False
    logger.warning("gspread module not found. Google Sheets integration will be disabled.")


class GoogleSheetsSync:
    """Google Sheets senkronizasyon sınıfı"""
    
    def __init__(self, sheet_key=None):
        """
        Args:
            sheet_key: Google Sheets document key (optional, can be set from config)
        """
        self.sheet_key = sheet_key
        self.creds_file = "service_account.json"
        
    def _get_sheets_client_sync(self):
        """
        Returns authorized gspread client (synchronous).
        Raises exception if gspread not available or credentials missing.
        """
        if gspread is None:
            raise ImportError("gspread module not installed")
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_file(self.creds_file, scopes=scope)
        return gspread.authorize(creds)
    
    async def update_sheet_player(self, steam_id, name, discord_id, delete=False):
        """
        Helper to sync single player changes to Google Sheet.
        
        Args:
            steam_id: Player's Steam ID
            name: Player name
            discord_id: Player's Discord ID (optional)
            delete: If True, delete the player row
        """
        if not GSPREAD_AVAILABLE or not self.sheet_key:
            return
        
        try:
            scope = [
                "https://spreadsheets.google.com/feeds", 
                'https://www.googleapis.com/auth/spreadsheets',
                "https://www.googleapis.com/auth/drive.file", 
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file(self.creds_file, scopes=scope)
            client = await asyncio.to_thread(gspread.authorize, creds)
            sheet = await asyncio.to_thread(client.open_by_key, self.sheet_key)
            worksheet = await asyncio.to_thread(lambda: sheet.sheet1)
            
            all_rows = await asyncio.to_thread(worksheet.get_all_values)
            if not all_rows: 
                return

            headers = [h.lower().strip() for h in all_rows[0]]
            idx_steam = -1
            idx_name = -1
            idx_discord = -1
            
            possible_steam = ["steam64id", "steamid", "steam_id", "steam id"]
            possible_name = ["player", "name", "isim", "oyuncu"]
            possible_discord = ["discord id", "discord_id", "discordid"]
            
            for i, h in enumerate(headers):
                if idx_steam == -1 and h in possible_steam: 
                    idx_steam = i
                if idx_name == -1 and h in possible_name: 
                    idx_name = i
                if idx_discord == -1 and h in possible_discord: 
                    idx_discord = i
            
            if idx_steam == -1: 
                return

            target_row_idx = -1
            for i, row in enumerate(all_rows):
                if i == 0: 
                    continue
                s_id = row[idx_steam].strip() if len(row) > idx_steam else ""
                if s_id == steam_id:
                    target_row_idx = i + 1  # 1-based index
                    break
            
            if delete:
                if target_row_idx != -1:
                    await asyncio.to_thread(worksheet.delete_rows, target_row_idx)
                    logger.info(f"Sheet Sync: Deleted {steam_id}")
            else:
                # Add or Update
                d_id_str = str(discord_id) if discord_id else ""
                
                if target_row_idx != -1:
                    # Update existing
                    if idx_name != -1: 
                        await asyncio.to_thread(worksheet.update_cell, target_row_idx, idx_name + 1, name)
                    if idx_discord != -1: 
                        await asyncio.to_thread(worksheet.update_cell, target_row_idx, idx_discord + 1, d_id_str)
                    logger.info(f"Sheet Sync: Updated {steam_id}")
                else:
                    # Append
                    new_row = [""] * len(headers)
                    new_row[idx_steam] = steam_id
                    if idx_name != -1: 
                        new_row[idx_name] = name
                    if idx_discord != -1: 
                        new_row[idx_discord] = d_id_str
                    await asyncio.to_thread(worksheet.append_row, new_row)
                    logger.info(f"Sheet Sync: Appended {steam_id}")

        except GoogleSheetsAPIError as e:
            logger.error(f"Sheet Sync Error ({steam_id}): {e}", exc_info=True)
    
    async def export_to_sheets_full(self, db_data, sheet_name="Whitelist"):
        """
        Internal function to export ENTIRE squad_db.json data to Google Sheets.
        This replaces the sheet contents with current DB data.
        Called automatically after DB modifications for full sync.
        
        Args:
            db_data: The squad_db.json dictionary
            sheet_name: Target sheet name (default: "Whitelist")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if gspread is None:
                logger.debug("⚠️ gspread not available, skipping Sheets sync")
                return False
            
            if not self.sheet_key:
                logger.warning("⚠️ GOOGLE_SHEET_KEY not configured, skipping Sheets sync")
                return False
            
            # Get client and perform export (sync operations, run in thread)
            def _sync_export():
                client = self._get_sheets_client_sync()
                spreadsheet = client.open_by_key(self.sheet_key)
                
                # Try to get sheet, create if doesn't exist
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                
                # Prepare data
                headers = ["Steam64ID", "Player", "Discord ID"]
                rows = [headers]
                
                for player in db_data.get("players", []):
                    steam_id = player.get("steam_id", "")
                    name = player.get("name", "")
                    discord_id = str(player.get("discord_id", "")) if player.get("discord_id") else ""
                    
                    rows.append([steam_id, name, discord_id])
                
                # Clear and update sheet (batch operation for speed)
                worksheet.clear()
                worksheet.update(rows, value_input_option='RAW')
                
                return len(rows) - 1  # Exclude header
            
            # Run in thread to avoid blocking
            exported_count = await asyncio.to_thread(_sync_export)
            logger.info(f"✅ Sheets auto-sync: {exported_count} oyuncu → '{sheet_name}'")
            return True
            
        except FileNotFoundError:
            logger.warning("⚠️ service_account.json not found, skipping Sheets sync")
            return False
        except GoogleSheetsAPIError as e:
            logger.error(f"❌ Sheets sync hatası: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error in Sheets sync: {e}", exc_info=True)
            logger.debug(traceback.format_exc())
            return False
    
    async def save_db_and_sync(self, data, db_file="squad_db.json"):
        """
        Save to squad_db.json AND automatically sync to Google Sheets.
        This is the PRIMARY function to use when modifying the database.
        
        Args:
            data: Complete database dictionary to save
            db_file: Path to JSON database file
        """
        # Update timestamp
        data["last_update"] = str(datetime.datetime.now())
        
        # 1. Save to JSON (critical - must succeed)
        def _write_json():
            with open(db_file, "w", encoding="utf-8") as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        await asyncio.to_thread(_write_json)
        logger.debug(f"💾 DB saved to {db_file}")
        
        # 2. Auto-sync to Sheets (non-critical - failure won't break functionality)
        try:
            await self.export_to_sheets_full(data)
        except GoogleSheetsAPIError as e:
            logger.warning(f"⚠️ Auto-sync to Sheets failed (DB still saved): {e}")
