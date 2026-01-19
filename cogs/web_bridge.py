"""
Web-Bot Bridge Cog
Processes web admin actions and triggers Discord bot responses
"""
import discord
from discord.ext import commands, tasks
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for database imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.adapter import DatabaseAdapter
from database.models import Base

logger = logging.getLogger("WebBridge")


class WebBridge(commands.Cog):
    """Bridge between web admin panel and Discord bot"""
    
    def __init__(self, bot):
        self.bot = bot
        # Use DEV database with proper SQLAlchemy URL format
        self.db = DatabaseAdapter('sqlite:///cotabot_dev.db')
        self.process_web_actions.start()
        logger.info("🌉 Web Bridge initialized")
    
    def cog_unload(self):
        """Cleanup on cog unload"""
        self.process_web_actions.cancel()
        logger.info("🌉 Web Bridge unloaded")
    
    @tasks.loop(seconds=10)
    async def process_web_actions(self):
        """Process pending web admin actions every 10 seconds"""
        try:
            actions = await self.db.get_pending_web_actions(limit=50)
            
            if not actions:
                return
            
            logger.info(f"📥 Processing {len(actions)} web actions...")
            
            for action in actions:
                try:
                    data = json.loads(action.data) if isinstance(action.data, str) else action.data
                    
                    # Route to appropriate handler
                    if action.action_type == 'announce_event':
                        await self.handle_event_announcement(data)
                    elif action.action_type == 'notify_player_add':
                        await self.handle_player_added(data)
                    elif action.action_type == 'notify_player_delete':
                        await self.handle_player_deleted(data)
                    else:
                        logger.warning(f"Unknown action type: {action.action_type}")
                    
                    # Mark as processed
                    await self.db.mark_action_processed(action.id)
                    logger.info(f"✅ Processed action {action.id}: {action.action_type}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing action {action.id}: {e}", exc_info=True)
                    await self.db.mark_action_failed(action.id, str(e))
                
                # Small delay between actions
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"❌ Error in process_web_actions loop: {e}", exc_info=True)
    
    @process_web_actions.before_loop
    async def before_process_web_actions(self):
        """Wait for bot to be ready before starting loop"""
        await self.bot.wait_until_ready()
        logger.info("🌉 Web Bridge ready, starting action processor...")
    
    async def handle_event_announcement(self, data: dict):
        """Announce event created from web admin to Discord"""
        channel_id = int(data.get('channel_id'))
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            raise Exception(f"Channel {channel_id} not found")
        
        # Parse timestamp
        timestamp_dt = datetime.fromisoformat(data['timestamp'])
        timestamp = int(timestamp_dt.timestamp())
        time_str = f"<t:{timestamp}:F> (<t:{timestamp}:R>)"
        
        # Create embed in the same format as !1duyuru command
        embed = discord.Embed(
            title=f"📅 {data['title']}",
            description=f"**Başlangıç:** {time_str}\n\n{data.get('description', '')}\n\nLütfen aşağıdaki butonları kullanarak katılım durumunuzu belirtiniz.",
            color=0x2ecc71  # SUCCESS color
        )
        
        # Set author (Web Admin)
        embed.set_author(name="Web Admin Tarafından Oluşturuldu")
        
        # Add participant fields
        embed.add_field(name="✅ Katılanlar (0)", value="-", inline=True)
        embed.add_field(name="❌ Katılmayanlar (0)", value="-", inline=True)
        embed.add_field(name="❔ Belki (0)", value="-", inline=True)
        
        # Set footer with event ID
        event_id = data.get('event_id')
        if event_id:
            embed.set_footer(text=f"Cotabot Event System | ID: {event_id}")
        
        # Send with optional @everyone mention and EventView buttons
        content = "@everyone" if data.get('mention_everyone', False) else None
        
        # Import EventView from event cog
        event_cog = self.bot.get_cog("Event")
        if event_cog:
            # Use the same EventView as !1duyuru command
            from cogs.event import EventView
            view = EventView()
            message = await channel.send(content=content, embed=embed, view=view)
        else:
            # Fallback without view if Event cog not loaded
            message = await channel.send(content=content, embed=embed)
        
        # Update event with message_id in database
        if event_id:
            await self.db.update_event_message(event_id, message.id)
            logger.info(f"📝 Updated event {event_id} with message ID {message.id}")
        
        logger.info(f"📢 Event announced: {data['title']} in channel {channel_id}")
    
    async def handle_player_added(self, data: dict):
        """Handle player added notification"""
        # TODO: Implement player add notification
        # Could send to a specific admin channel
        logger.info(f"👤 Player added: {data.get('player_name')}")
    
    async def handle_player_deleted(self, data: dict):
        """Handle player deleted notification"""
        # TODO: Implement player delete notification
        logger.info(f"👤 Player deleted: {data.get('player_name')}")
    
    @commands.command(name='web_status')
    @commands.has_permissions(administrator=True)
    async def web_status(self, ctx):
        """Check web bridge status and pending actions"""
        pending = await self.db.get_pending_web_actions(limit=100)
        
        embed = discord.Embed(
            title="🌉 Web Bridge Status",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Status",
            value="✅ Active" if self.process_web_actions.is_running() else "❌ Stopped",
            inline=True
        )
        
        embed.add_field(
            name="Pending Actions",
            value=str(len(pending)),
            inline=True
        )
        
        if pending:
            action_summary = {}
            for action in pending[:10]:
                action_summary[action.action_type] = action_summary.get(action.action_type, 0) + 1
            
            summary_text = "\n".join([f"• {k}: {v}" for k, v in action_summary.items()])
            embed.add_field(
                name="Action Types",
                value=summary_text or "None",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(WebBridge(bot))
