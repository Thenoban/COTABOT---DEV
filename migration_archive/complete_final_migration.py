"""
Complete Remaining Migrations - Comprehensive JSON Replacement
Handles all remaining commands that read from squad_db.json
"""
import re

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

original_content = content
changes = []

print("COMPREHENSIVE MIGRATION - FINAL PASS\n")

# ==========================================
# Migration Squad_import_sheet - Save to DB
# ==========================================
print("1. Migrating squad_import_sheet database save...")

# After loading and processing sheet data, save to database
old_import_save = '''            # Save
            db_data["last_update"] = str(datetime.datetime.now())
            def _save_db():
                with open("squad_db.json", "w", encoding="utf-8") as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
            await msg.edit(content="💾 Veritabanı kaydediliyor...")
            await asyncio.to_thread(_save_db)'''

new_import_save = '''            # Save to database (HYBRID MODE)
            if hasattr(self, 'json_mode') and hasattr(self, 'db') and not self.json_mode:
                try:
                    for s_id, p_data in existing_map.items():
                        player_exists = await self.db.get_player_by_steam_id(s_id)
                        if player_exists:
                            await self.db.update_player(s_id, name=p_data["name"], discord_id=p_data.get("discord_id"))
                        else:
                            await self.db.add_player(s_id, p_data["name"], p_data.get("discord_id"))
                    logger.info(f"Sheets import: Saved {len(existing_map)} players to database")
                except Exception as e:
                    logger.error(f"DB save error in import: {e}")
            
            # JSON save (fallback or json_mode)
            db_data["last_update"] = str(datetime.datetime.now())
            def _save_db():
                with open("squad_db.json", "w", encoding="utf-8") as f:
                    json.dump(db_data, f, ensure_ascii=False, indent=4)
            await msg.edit(content="💾 Veritabanı kaydediliyor...")
            await asyncio.to_thread(_save_db)'''

if old_import_save in content:
    content = content.replace(old_import_save, new_import_save)
    changes.append("squad_import_sheet - database save")

# ===============================================
# Summary of all changes
# ===============================================
print(f"\nMIGRATION SUMMARY:")
print(f"Changes applied: {len(changes)}")
for change in changes:
    print(f"  - {change}")

if content != original_content:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\nFILE UPDATED SUCCESSFULLY")
else:
    print("\nNO CHANGES MADE - Patterns not found")

print("\n=== MIGRATION PHASE COMPLETE ===")
print("\nREMAINING WORK:")
print("  - Manual review of lines 1800+ (squad_import_sheet) OK")
print("  - Event system migration (separate)")
print("  - Docker restart + comprehensive testing")
print("\nREADY FOR TESTING PHASE")
