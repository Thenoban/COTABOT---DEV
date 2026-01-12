# New Google Sheets Activity Panel Functions
# To be integrated into squad_players.py after line 2706

import datetime
import discord
import logging

logger = logging.getLogger("SquadPlayers")

ACTIVITY_SHEET_ID = '1GAmtAqOSOh5DplcufyqvKepcepgfo-ORsfWXThbP_s8'

async def fetch_activity_from_sheets(self, force=False):
    """Fetch activity data from Google Sheets with smart G2 timestamp caching"""
    try:
        if not hasattr(self, 'gc') or not self.gc:
            logger.warning("Google Sheets client not initialized")
            return getattr(self, '_cached_activity_data', [])
        
        sheet = self.gc.open_by_key(ACTIVITY_SHEET_ID)
        worksheet = sheet.get_worksheet(0)  # First sheet
        
        # Check G2 for last update timestamp
        last_update_cell = worksheet.acell('G2').value
        
        # Compare with cached timestamp
        cached_timestamp = getattr(self, '_last_sheet_update', None)
        
        if not force and cached_timestamp == last_update_cell:
            logger.info(f"Sheet data unchanged (G2: {last_update_cell})")
            return getattr(self, '_cached_activity_data', [])
        
        # Fetch fresh data
        all_values = worksheet.get_all_values()[1:]  # Skip header
        
        activity_data = []
        for row in all_values:
            if len(row) >= 1 and row[0]:  # Has name
                activity_data.append({
                    'name': row[0],
                    'steam_id': row[1] if len(row) > 1 else '',
                    'playtime_2weeks': self._parse_playtime(row[2]) if len(row) > 2 else 0,
                    'leave_status': row[3] if len(row) > 3 else 'Aktif'
                })
        
        # Cache data and timestamp
        self._cached_activity_data = activity_data
        self._last_sheet_update = last_update_cell
        
        logger.info(f"Sheet data updated (G2: {last_update_cell}, {len(activity_data)} players)")
        return activity_data
        
    except Exception as e:
        logger.error(f"Sheets fetch error: {e}", exc_info=True)
        return getattr(self, '_cached_activity_data', [])

def _parse_playtime(self, value):
    """Convert sheet playtime value to minutes"""
    if not value:
        return 0
    
    try:
        # Try direct number (minutes)
        return int(float(value))
    except:
        # Try formats like "2828 dk" or "47 saat" or "47.2"
        value_str = str(value).lower().replace(',', '.')
        
        if 'saat' in value_str or 'hour' in value_str:
            # Extract number and convert hours to minutes
            num = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
            return int(num * 60)
        elif 'dk' in value_str or 'min' in value_str:
            # Extract minutes
            num = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
            return int(num)
        else:
            # Try as raw number
            num = float(''.join(c for c in value_str if c.isdigit() or c == '.'))
            return int(num)
    
    return 0

async def generate_activity_panel_sheets(self, activity_data):
    """Generate activity panel embed from Sheets data"""
    
    # Separate active vs on-leave players
    on_leave_keywords = ['izinli', 'izin', 'izinde', 'leave']
    active_players = [p for p in activity_data if p['leave_status'].lower() not in on_leave_keywords]
    on_leave = [p for p in activity_data if p['leave_status'].lower() in on_leave_keywords]
    
    # Sort by playtime (descending)
    active_players.sort(key=lambda x: x['playtime_2weeks'], reverse=True)
    
    embed = discord.Embed(
        title="🎮 AKTİFLİK SIRALAMASI",
        description="**Son 2 Hafta** • Google Sheets verilerine göre",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    # Top 10 ranking
    top_10_text = ""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, player in enumerate(active_players[:10]):
        hours = player['playtime_2weeks'] / 60
        medal = medals[i] if i < len(medals) else f"{i+1}."
        top_10_text += f"{medal} **{player['name']}** - {hours:.1f} saat\n"
    
    if not top_10_text:
        top_10_text = "Veri bulunamadı"
    
    embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━", value=top_10_text, inline=False)
    
    # Statistics
    total_active = len(active_players)
    avg_time = sum(p['playtime_2weeks'] for p in active_players) / total_active if total_active > 0 else 0
    top_player = active_players[0] if active_players else None
    
    stats_text = f"📊 **Toplam Aktif:** {total_active} oyuncu\n"
    stats_text += f"⏱️ **Ortalama:** {avg_time/60:.1f} saat\n"
    if top_player:
        stats_text += f"🏆 **En Aktif:** {top_player['name']} ({top_player['playtime_2weeks']/60:.1f} saat)"
    
    embed.add_field(name="📈 İstatistikler", value=stats_text, inline=False)
    
    # On-leave players
    if on_leave:
        leave_text = "\n".join([f"• {p['name']}" for p in on_leave[:10]])
        if len(on_leave) > 10:
            leave_text += f"\n... ve {len(on_leave) - 10} oyuncu daha"
        embed.add_field(name=f"🌴 İzinli Oyuncular ({len(on_leave)})", value=leave_text, inline=False)
    
    # Update timestamp from G2
    last_update = getattr(self, '_last_sheet_update', 'Bilinmiyor')
    embed.set_footer(text=f"Veri Kaynağı: Google Sheets • Son Güncelleme: {last_update}")
    
    return embed
