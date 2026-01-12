import os
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import socket
import sys
import asyncio
import aiohttp
import datetime

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Main")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


# Intents setup
intents = discord.Intents.all()

# Bot setup with prefix '!1' for DEV environment
proxy_url = os.getenv("http_proxy") or os.getenv("HTTP_PROXY")
# Ensure proxy settings are passed correctly to aiohttp if needed, 
# though discord.py handles 'proxy' arg for the websocket.
bot = commands.Bot(command_prefix='!1', intents=intents, proxy=proxy_url, help_command=None)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="COTABOT"))
    logger.info(f'{bot.user} olarak giriş yapıldı!')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

async def load_extensions():
    # Klasor yoksa olustur
    if not os.path.exists('./cogs'):
        os.makedirs('./cogs')
    
    logger.info("Extension yükleme başladı...")
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f'{filename} BAŞARIYLA yüklendi.')
            except Exception as e:
                logger.error(f'XXX {filename} yüklenirken HATA: {e}', exc_info=True)

async def main():
    async with bot:
        await load_extensions()
        
        # Proxy connection retry loop
        max_retries = 10
        for i in range(max_retries):
            try:
                await bot.start(TOKEN)
            except (OSError, aiohttp.ClientConnectorError) as e:
                if "Connect call failed" in str(e) or "Cannot connect to host" in str(e):
                    logger.warning(f"Proxy Connection Refused (Attempt {i+1}/{max_retries}). Retrying in 5s...")
                    await asyncio.sleep(5)
                else:
                    raise e
            except Exception as e:
                # If it's not a connection error, raise it
                raise e

if __name__ == '__main__':
    logger.info("--- BOT BAŞLATILIYOR ---")

    if TOKEN:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            # Handle Ctrl+C cleanly
            pass
        except Exception as e:
            logger.critical(f"CRITICAL ERROR: {e}", exc_info=True)
    else:
        logger.critical("Hata: .env dosyasında DISCORD_TOKEN bulunamadı.")
