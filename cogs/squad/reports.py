"""
Squad Players - Reports System
Otomatik raporlama, snapshot ve delta hesaplama sistemi
"""
import os
import json
import datetime
import discord
from discord.ext import tasks
import asyncio
import logging

# Import custom exceptions
from exceptions import DatabaseError, DiscordOperationError

logger = logging.getLogger("SquadPlayers.Reports")


class ReportSystem:
    """Rapor sistemi - snapshot, delta calculation, automated reporting"""
    
    def __init__(self, bot, db=None, json_mode=False):
        """
        Args:
            bot: Discord bot instance
            db: DatabaseAdapter instance (optional)
            json_mode: If True, use JSON fallback instead of database
        """
        self.bot = bot
        self.db = db
        self.json_mode = json_mode
        self.report_file = "squad_reports.json"
        
    def _get_report_db(self):
        """Load report database from JSON"""
        if os.path.exists(self.report_file):
            try:
                with open(self.report_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: 
                return {}
        return {}

    def _save_report_db(self, data):
        """Save report database to JSON"""
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    async def take_snapshot(self, period="weekly"):
        """
        Takes a snapshot of current stats for delta calculation
        
        Args:
            period: 'weekly' or 'monthly'
            
        Returns:
            True if successful
        """
        # HYBRID: Use database if available
        if hasattr(self, 'db') and self.db and not self.json_mode:
            try:
                # Create snapshot in database
                snapshot_id = await self.db.create_snapshot(period)
                
                # Store metadata
                await self.db.set_report_metadata(f"last_{period}", str(datetime.datetime.now()))
                await self.db.set_report_metadata(f"last_{period}_snapshot_id", str(snapshot_id))
                
                logger.info(f"Created {period} snapshot in database (ID: {snapshot_id})")
                return True
            except DatabaseError as e:
                logger.error(f"Database snapshot error: {e}, falling back to JSON", exc_info=True)
        
        # JSON FALLBACK
        if not os.path.exists("squad_db.json"): 
            return False
            
        with open("squad_db.json", "r", encoding="utf-8") as f:
            current_db = json.load(f)
        
        snapshot = {}
        for p in current_db.get("players", []):
            sid = p.get("steam_id")
            stats = p.get("stats", {})
            if sid and stats:
                snapshot[sid] = {
                    "score": stats.get("totalScore", 0),
                    "kills": stats.get("totalKills", 0),
                    "deaths": stats.get("totalDeaths", 0),
                    "revives": stats.get("totalRevives", 0),
                    "wounds": stats.get("totalWounds", 0),
                    "kd": stats.get("totalKdRatio", 0)
                }
        
        report_data = self._get_report_db()
        if "snapshots" not in report_data: 
            report_data["snapshots"] = {}
        report_data["snapshots"][period] = {
            "timestamp": str(datetime.datetime.now()),
            "data": snapshot
        }
        if "meta" not in report_data: 
            report_data["meta"] = {}
        report_data["meta"][f"last_{period}"] = str(datetime.datetime.now())
        self._save_report_db(report_data)
        return True

    async def calculate_deltas(self, period="weekly"):
        """
        Compares Current DB vs Snapshot[period]
        
        Args:
            period: 'weekly' or 'monthly'
            
        Returns:
            List of player delta objects
        """
        # HYBRID: Use database if available
        if hasattr(self, 'db') and self.db and not self.json_mode:
            try:
                # Get latest snapshot ID
                snapshot_id_str = await self.db.get_report_metadata(f"last_{period}_snapshot_id")
                if not snapshot_id_str:
                    logger.warning(f"No snapshot found for {period}")
                    return []
                
                snapshot_id = int(snapshot_id_str)
                
                # Calculate deltas from snapshot to current
                db_deltas = await self.db.calculate_deltas(snapshot_id)
                
                # Normalize keys for compatibility with reports.py logic
                deltas = []
                for d in db_deltas:
                    d_norm = d.copy()
                    d_norm['score'] = d.get('score_delta', 0)
                    d_norm['kills'] = d.get('kills_delta', 0)
                    d_norm['deaths'] = d.get('deaths_delta', 0)
                    d_norm['revives'] = d.get('revives_delta', 0)
                    # d_norm['wounds'] missing in DB calculator? optional
                    d_norm['name'] = d.get('player_name', 'Unknown')
                    # KD calc if not present
                    k = d_norm['kills']
                    d_val = d_norm['deaths']
                    d_norm['kd'] = k / d_val if d_val > 0 else k
                    deltas.append(d_norm)
                
                logger.info(f"Calculated {len(deltas)} deltas for {period} from database")
                return deltas
                
            except DatabaseError as e:
                logger.error(f"Database delta calculation error: {e}, falling back to JSON", exc_info=True)
        
        # JSON FALLBACK
        if not os.path.exists("squad_db.json"): 
            return []
            
        with open("squad_db.json", "r", encoding="utf-8") as f:
            current_db = json.load(f)
            
        report_data = self._get_report_db()
        snapshot_data = report_data.get("snapshots", {}).get(period, {}).get("data", {})
        
        if not snapshot_data:
            return []  # No snapshot to compare against
            
        deltas = []
        
        for p in current_db.get("players", []):
            sid = p.get("steam_id")
            name = p.get("name")
            curr_stats = p.get("stats", {})
            
            if not sid: 
                continue
            
            snap_stats = snapshot_data.get(sid, {})
            
            d_score = curr_stats.get("totalScore", 0) - snap_stats.get("score", 0)
            d_kills = curr_stats.get("totalKills", 0) - snap_stats.get("kills", 0)
            d_deaths = curr_stats.get("totalDeaths", 0) - snap_stats.get("deaths", 0)
            d_revives = curr_stats.get("totalRevives", 0) - snap_stats.get("revives", 0)
            
            # Filter inactive or zero-change players
            if d_score <= 0 and d_kills <= 0: 
                continue
            
            deltas.append({
                "name": name,
                "steam_id": sid,
                "score": d_score,
                "kills": d_kills,
                "deaths": d_deaths,
                "revives": d_revives,
                "kd": d_kills / d_deaths if d_deaths > 0 else d_kills
            })
            
        return deltas
    
    def save_to_history(self, period, deltas):
        """
        Save report data to history array for trend analysis
        
        Args:
            period: 'weekly' or 'monthly'
            deltas: Player delta data from calculate_deltas()
        """
        if not deltas:
            return
        
        report_db = self._get_report_db()
        
        # Initialize history structure
        if "history" not in report_db:
            report_db["history"] = {"weekly": [], "monthly": []}
        
        # Sort players by score
        top_players = sorted(deltas, key=lambda x: x.get('score', 0), reverse=True)
        top_10 = top_players[:10]
        
        # Find best performers
        best_kills = max(deltas, key=lambda x: x.get('kills', 0))
        best_kd = max(deltas, key=lambda x: x.get('kd', 0))
        
        # Create history entry
        history_entry = {
            "timestamp": str(datetime.datetime.now()),
            "period": period,
            "top_10": top_10,
            "best_kills": best_kills,
            "best_kd": best_kd,
            "total_players": len(deltas)
        }
        
        # Add to history (maintain max 52 weeks or 12 months)
        max_entries = 52 if period == "weekly" else 12
        report_db["history"][period].append(history_entry)
        report_db["history"][period] = report_db["history"][period][-max_entries:]
        
        self._save_report_db(report_db)
        logger.info(f"Saved {period} report to history")

    async def publish_report(self, guild, period, channel=None):
        """
        Publish report to Discord channel
        
        Args:
            guild: Discord guild
            period: 'weekly' or 'monthly'
            channel: Target channel (optional, defaults to #rapor-log)
        """
        deltas = await self.calculate_deltas(period)
        if not deltas: 
            return
        
        embed = self.create_report_embed(deltas, period, preview=False)
        
        # Generate charts
        try:
            from .utils.chart_maker import generate_report_charts
            chart_buf = await asyncio.to_thread(generate_report_charts, deltas, period)
            file = discord.File(chart_buf, filename="report_charts.png")
            embed.set_image(url="attachment://report_charts.png")
        except ImportError as e:
            logger.error(f"Chart generation import failed: {e}")
            file = None
        except Exception as e:
            logger.error(f"Chart generation failed: {e}", exc_info=True)
            file = None
        
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="rapor-log")
            if not channel:
                # Fallback: squad-log
                channel = discord.utils.get(guild.text_channels, name="squad-log")
        
        if channel:
            if file:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
        else:
            logger.warning(f"Report Generation Failed: No suitable channel found in {guild.name}")

    def create_report_embed(self, deltas, period, preview=False):
        """
        Create Discord embed for report
        
        Args:
            deltas: List of player deltas
            period: 'weekly' or 'monthly'
            preview: If True, add preview tag
            
        Returns:
            discord.Embed
        """
        # Sorts
        top_score = sorted(deltas, key=lambda x: x["score"], reverse=True)[:1]
        top_kill = sorted(deltas, key=lambda x: x["kills"], reverse=True)[:1]
        top_revive = sorted(deltas, key=lambda x: x["revives"], reverse=True)[:1]
        
        # Leaderboard (Score)
        leaderboard = sorted(deltas, key=lambda x: x["score"], reverse=True)[:10]

        period_map = {"weekly": "Haftalık", "monthly": "Aylık", "daily": "Günlük"}
        title_p = period_map.get(period, period.capitalize())
        
        embed = discord.Embed(
            title=f"📊 {title_p} Sunucu Raporu" + (" (Önizleme)" if preview else ""),
            color=discord.Color.gold() if not preview else discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        if top_score:
            mvp = top_score[0]
            embed.add_field(
                name="🏆 HAFTANIN MVP'si", 
                value=f"**{mvp['name']}**\n📈 +{mvp['score']} Puan", 
                inline=False
            )
            
        # Inline Stats
        killer_txt = f"**{top_kill[0]['name']}** ({top_kill[0]['kills']} Kill)" if top_kill else "-"
        medic_txt = f"**{top_revive[0]['name']}** ({top_revive[0]['revives']} Revive)" if top_revive else "-"
        
        embed.add_field(name="⚔️ En Çok Adam Vuran", value=killer_txt, inline=True)
        embed.add_field(name="🚑 En İyi Doktor", value=medic_txt, inline=True)
        
        # List
        lb_text = []
        for i, p in enumerate(leaderboard, 1):
            icon = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            lb_text.append(f"{icon} **{p['name']}** - {p['score']} Puan | {p['kills']} K | {p['deaths']} D")
            
        embed.add_field(
            name="📜 Puan Sıralaması (Top 10)", 
            value="\n".join(lb_text) if lb_text else "Veri Yok", 
            inline=False
        )
        
        if not preview:
            embed.set_footer(text="İstatistikler sıfırlandı. Yeni dönem başladı.")
        
        return embed
    
    @tasks.loop(hours=1)
    async def automated_report_loop(self):
        """Checks periodically if a scheduled report (Weekly/Monthly) is due"""
        now = datetime.datetime.now()
        report_db = self._get_report_db()
        meta = report_db.get("meta", {})
        
        # Load metadata from DB if available
        if self.db and not self.json_mode:
            try:
                last_w = await self.db.get_report_metadata("last_weekly")
                if last_w: meta["last_weekly"] = last_w
                
                last_m = await self.db.get_report_metadata("last_monthly")
                if last_m: meta["last_monthly"] = last_m
            except:
                pass
        
        # --- WEEKLY REPORT ---
        # Monday = 0. Run if it is Monday.
        if now.weekday() == 0 and now.hour >= 9:  # After 9 AM
            last_run_str = meta.get("last_weekly")
            should_run = True
            
            if last_run_str:
                last_run = datetime.datetime.fromisoformat(last_run_str)
                # If last run was less than 4 days ago, don't run again
                if (now - last_run).days < 4:
                    should_run = False
            
            if should_run:
                # Calculate deltas BEFORE taking new snapshot
                deltas = await self.calculate_deltas("weekly")
                
                # Save to history (DB or JSON)
                if self.db and not self.json_mode and deltas:
                    try:
                        # Get snapshot ID again to be safe
                        snap_id = await self.db.get_report_metadata(f"last_weekly_snapshot_id")
                        if snap_id:
                            # Remap keys back to adapter expectations
                            db_payload = []
                            for i, d in enumerate(deltas, 1):
                                db_payload.append({
                                    'steam_id': d['steam_id'],
                                    'player_name': d['name'],
                                    'score_delta': d['score'],
                                    'kills_delta': d['kills'],
                                    'deaths_delta': d['deaths'],
                                    'revives_delta': d['revives'],
                                    'rank': i
                                })
                            
                            await self.db.save_report_delta("weekly", int(snap_id), db_payload)
                            logger.info("Saved Weekly Report to Database")
                    except Exception as e:
                        logger.error(f"Failed to save weekly report to DB: {e}")
                
                # Also save to JSON history for backup/legacy
                if deltas:
                    self.save_to_history("weekly", deltas)
                
                # Publish to all guilds
                for guild in self.bot.guilds:
                    try:
                        await self.publish_report(guild, "weekly")
                        logger.info(f"Published Automated Weekly Report for {guild.name}")
                    except DiscordOperationError as e:
                        logger.error(f"Failed to auto-publish weekly report: {e}", exc_info=True)
                
                # Take Snapshot & Update Meta (AFTER history save)
                await self.take_snapshot("weekly")
                meta["last_weekly"] = now.isoformat()
                self._save_report_db(report_db)
                logger.info("Automated Weekly Snapshot Taken.")
        
        # --- MONTHLY REPORT ---
        # Run on 1st of month, after 10 AM
        if now.day == 1 and now.hour >= 10:
            last_monthly = meta.get("last_monthly")
            should_run = True
            
            if last_monthly:
                last = datetime.datetime.fromisoformat(last_monthly)
                # If last run was less than 20 days ago, skip
                if (now - last).days < 20:
                    should_run = False
            
            if should_run:
                # Calculate deltas BEFORE taking new snapshot
                deltas = await self.calculate_deltas("monthly")
                
                # Save to history (DB or JSON)
                if self.db and not self.json_mode and deltas:
                    try:
                        # Get snapshot ID again to be safe
                        snap_id = await self.db.get_report_metadata(f"last_monthly_snapshot_id")
                        if snap_id:
                            # Remap keys back to adapter expectations
                            db_payload = []
                            for i, d in enumerate(deltas, 1):
                                db_payload.append({
                                    'steam_id': d['steam_id'],
                                    'player_name': d['name'],
                                    'score_delta': d['score'],
                                    'kills_delta': d['kills'],
                                    'deaths_delta': d['deaths'],
                                    'revives_delta': d['revives'],
                                    'rank': i
                                })
                            
                            await self.db.save_report_delta("monthly", int(snap_id), db_payload)
                            logger.info("Saved Monthly Report to Database")
                    except Exception as e:
                        logger.error(f"Failed to save monthly report to DB: {e}")
                
                # Also save to JSON history for backup/legacy
                if deltas:
                    self.save_to_history("monthly", deltas)
                
                for guild in self.bot.guilds:
                    try:
                        await self.publish_report(guild, "monthly")
                        logger.info(f"Published Automated Monthly Report for {guild.name}")
                    except DiscordOperationError as e:
                        logger.error(f"Failed to auto-publish monthly report: {e}", exc_info=True)
                
                # Take Snapshot & Update Meta (AFTER history save)
                await self.take_snapshot("monthly")
                meta["last_monthly"] = now.isoformat()
                self._save_report_db(report_db)
                logger.info("Automated Monthly Snapshot Taken.")

    @automated_report_loop.before_loop
    async def before_report_loop(self):
        """Wait until bot is ready before starting loop"""
        await self.bot.wait_until_ready()
