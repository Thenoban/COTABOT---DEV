import discord
from discord.ext import commands, tasks
import os
import json
import shutil
import datetime
import zipfile
import logging
from .utils.config import ADMIN_USER_IDS, ADMIN_ROLE_IDS, COLORS

logger = logging.getLogger("Backup")

class Backup(commands.Cog):
    """Otomatik yedekleme sistemi - Kritik verileri korur"""
    
    def __init__(self, bot):
        self.bot = bot
        self.backup_dir = "backups"
        self.critical_files = [
            "squad_db.json",
            "voice_stats.json",
            "squad_reports.json",
            "events.json",
            "activity_panel.json",
            "squad_activity.json"
        ]
        self.retention_days = 7
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Start automated backup loop
        self.daily_backup_task.start()
    
    def cog_unload(self):
        self.daily_backup_task.cancel()
    
    async def check_admin(self, ctx):
        """Check if user is admin"""
        if ctx.author.id in ADMIN_USER_IDS:
            return True
        if hasattr(ctx.author, 'roles'):
            for role in ctx.author.roles:
                if role.id in ADMIN_ROLE_IDS:
                    return True
        await ctx.send("❌ Bu komutu kullanma yetkiniz yok.")
        return False
    
    def validate_json(self, filepath):
        """Validate that a file is valid JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except:
            return False
    
    async def create_backup(self, backup_name=None):
        """
        Create a backup of all critical files.
        Returns (success: bool, message: str, backup_path: str)
        """
        if backup_name is None:
            backup_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        backup_path = os.path.join(self.backup_dir, backup_name)
        os.makedirs(backup_path, exist_ok=True)
        
        backed_up = []
        skipped = []
        
        for filename in self.critical_files:
            if not os.path.exists(filename):
                skipped.append(f"{filename} (dosya yok)")
                continue
            
            # Validate JSON before backup
            if filename.endswith('.json'):
                if not self.validate_json(filename):
                    skipped.append(f"{filename} (geçersiz JSON)")
                    logger.warning(f"Backup skipped invalid JSON: {filename}")
                    continue
            
            try:
                # Copy file to backup directory
                dest = os.path.join(backup_path, filename)
                shutil.copy2(filename, dest)
                backed_up.append(filename)
                logger.info(f"Backed up: {filename}")
            except Exception as e:
                skipped.append(f"{filename} ({str(e)})")
                logger.error(f"Backup failed for {filename}: {e}")
        
        # Create zip archive
        try:
            zip_path = f"{backup_path}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in backed_up:
                    file_path = os.path.join(backup_path, filename)
                    zipf.write(file_path, filename)
            
            # Remove uncompressed directory
            shutil.rmtree(backup_path)
            
            msg = f"✅ Yedekleme tamamlandı: `{backup_name}.zip`\n"
            msg += f"📦 Yedeklenen: {len(backed_up)} dosya\n"
            if skipped:
                msg += f"⚠️ Atlanan: {len(skipped)} dosya"
            
            logger.info(f"Backup created: {zip_path}")
            return True, msg, zip_path
            
        except Exception as e:
            logger.error(f"Zip creation failed: {e}")
            return False, f"❌ Sıkıştırma hatası: {e}", None
    
    async def cleanup_old_backups(self):
        """Remove backups older than retention_days"""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)
        removed = []
        
        try:
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                
                # Check if it's a backup file/directory
                if item.endswith('.zip') or os.path.isdir(item_path):
                    # Get modification time
                    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                    
                    if mtime < cutoff:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                        removed.append(item)
                        logger.info(f"Removed old backup: {item}")
            
            return removed
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return []
    
    @tasks.loop(hours=24)
    async def daily_backup_task(self):
        """Automated daily backup at 3 AM"""
        now = datetime.datetime.now()
        
        # Only run at 3 AM (with 1 hour window)
        if now.hour != 3:
            return
        
        logger.info("Running automated daily backup...")
        success, msg, backup_path = await self.create_backup()
        
        if success:
            # Cleanup old backups
            removed = await self.cleanup_old_backups()
            if removed:
                logger.info(f"Cleaned up {len(removed)} old backups")
            
            # Send notification to admin (optional)
            # You could add a notification channel here
    
    @daily_backup_task.before_loop
    async def before_daily_backup(self):
        await self.bot.wait_until_ready()
    
    @commands.command(name='backup_now')
    async def backup_now(self, ctx):
        """Manuel olarak hemen yedek oluşturur."""
        if not await self.check_admin(ctx):
            return
        
        msg = await ctx.send("📦 Yedekleme başlatılıyor...")
        
        success, result_msg, backup_path = await self.create_backup()
        
        embed = discord.Embed(
            title="💾 Manuel Yedekleme",
            description=result_msg,
            color=discord.Color(COLORS.SUCCESS if success else COLORS.ERROR)
        )
        
        if success:
            # Get file size
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            embed.add_field(name="Boyut", value=f"{size_mb:.2f} MB", inline=True)
        
        await msg.edit(content=None, embed=embed)
    
    @commands.command(name='backup_list')
    async def backup_list(self, ctx):
        """Mevcut yedekleri listeler."""
        if not await self.check_admin(ctx):
            return
        
        try:
            backups = []
            for item in os.listdir(self.backup_dir):
                if item.endswith('.zip'):
                    item_path = os.path.join(self.backup_dir, item)
                    size_mb = os.path.getsize(item_path) / (1024 * 1024)
                    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                    backups.append((item, size_mb, mtime))
            
            if not backups:
                await ctx.send("📭 Henüz yedek bulunamadı.")
                return
            
            # Sort by date (newest first)
            backups.sort(key=lambda x: x[2], reverse=True)
            
            embed = discord.Embed(
                title="📋 Mevcut Yedekler",
                color=discord.Color(COLORS.INFO)
            )
            
            desc = ""
            for name, size, mtime in backups[:10]:  # Show last 10
                date_str = mtime.strftime("%Y-%m-%d %H:%M")
                desc += f"📦 `{name}`\n"
                desc += f"   └ {size:.2f} MB • {date_str}\n\n"
            
            if len(backups) > 10:
                desc += f"*...ve {len(backups)-10} yedek daha*"
            
            embed.description = desc
            embed.set_footer(text=f"Toplam: {len(backups)} yedek • Saklama: {self.retention_days} gün")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Liste hatası: {e}")
    
    @commands.command(name='backup_restore')
    async def backup_restore(self, ctx, backup_name: str, filename: str):
        """
        Belirli bir dosyayı yedekten geri yükler.
        Kullanım: !backup_restore 2026-01-09_03-00-00.zip squad_db.json
        """
        if not await self.check_admin(ctx):
            return
        
        # Safety confirmation
        confirm_msg = await ctx.send(
            f"⚠️ **UYARI:** `{filename}` dosyasını `{backup_name}` yedeğinden geri yüklemek üzeresiniz.\n"
            f"Bu işlem mevcut dosyanın **üzerine yazacaktır**.\n\n"
            f"Devam etmek için ✅ ile onaylayın (30 saniye)."
        )
        
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirm_msg.edit(content="❌ Geri yükleme iptal edildi.")
                return
            
            # Proceed with restore
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            if not os.path.exists(backup_path):
                await confirm_msg.edit(content=f"❌ Yedek bulunamadı: `{backup_name}`")
                return
            
            # Extract file from zip
            try:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    if filename not in zipf.namelist():
                        await confirm_msg.edit(content=f"❌ Dosya yedekte bulunamadı: `{filename}`")
                        return
                    
                    # Extract to temp location first
                    temp_file = f"{filename}.restore_temp"
                    with zipf.open(filename) as source, open(temp_file, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    # Validate if JSON
                    if filename.endswith('.json'):
                        if not self.validate_json(temp_file):
                            os.remove(temp_file)
                            await confirm_msg.edit(content=f"❌ Yedekteki dosya geçersiz (bozuk JSON)")
                            return
                    
                    # Backup current file (just in case)
                    if os.path.exists(filename):
                        safety_backup = f"{filename}.before_restore"
                        shutil.copy2(filename, safety_backup)
                    
                    # Atomic rename
                    shutil.move(temp_file, filename)
                    
                    logger.info(f"Restored {filename} from {backup_name}")
                    await confirm_msg.edit(content=f"✅ `{filename}` başarıyla geri yüklendi!\n💡 Değişikliklerin etkili olması için botu yeniden başlatmanız gerekebilir.")
                    
            except Exception as e:
                await confirm_msg.edit(content=f"❌ Geri yükleme hatası: {e}")
                logger.error(f"Restore error: {e}")
                
        except TimeoutError:
            await confirm_msg.edit(content="⏱️ Zaman aşımı - İşlem iptal edildi.")
    
    @commands.command(name='backup_cleanup')
    async def backup_cleanup_cmd(self, ctx):
        """Eski yedekleri manuel olarak temizler (7 günden eski)."""
        if not await self.check_admin(ctx):
            return
        
        msg = await ctx.send("🧹 Eski yedekler temizleniyor...")
        
        removed = await self.cleanup_old_backups()
        
        if removed:
            embed = discord.Embed(
                title="🧹 Temizlik Tamamlandı",
                description=f"**{len(removed)}** eski yedek silindi.",
                color=discord.Color(COLORS.SUCCESS)
            )
            if len(removed) <= 5:
                embed.add_field(name="Silinenler", value="\n".join([f"• {r}" for r in removed]))
        else:
            embed = discord.Embed(
                title="🧹 Temizlik",
                description="Silinecek eski yedek bulunamadı.",
                color=discord.Color(COLORS.INFO)
            )
        
        await msg.edit(content=None, embed=embed)

async def setup(bot):
    await bot.add_cog(Backup(bot))
