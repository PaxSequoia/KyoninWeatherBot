import os
import discord
from discord.ext import commands, tasks
import mysql.connector
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MYSQL_HOST = os.getenv("DATABASE_HOST")
MYSQL_USER = os.getenv("DATABASE_USER")
MYSQL_PASSWORD = os.getenv("DATABASE_PASSWORD")
MYSQL_DATABASE = os.getenv("DATABASE_NAME")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Database connection
def get_mysql_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

# Get a forecast string (mock implementation, replace with actual DB fetch)
def generate_daily_forecast():
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT message FROM forecasts ORDER BY RAND() LIMIT 1;")
        result = cursor.fetchone()
        return result[0] if result else "No forecast available today."
    except Exception as e:
        logger.error(f"Error fetching forecast: {e}")
        return "Error generating forecast."
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Store last posted date to prevent duplicate daily posts
last_posted_date = None

@tasks.loop(minutes=15)
async def post_daily_forecast():
    global last_posted_date
    now = datetime.now(ZoneInfo("America/Chicago"))
    today_str = now.strftime('%Y-%m-%d')

    if last_posted_date == today_str:
        return

    if now.hour == 0 and now.minute < 15:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            forecast = generate_daily_forecast()
            await channel.send(forecast)
            last_posted_date = today_str
            logger.info("Forecast posted successfully.")
        else:
            logger.error("Channel not found.")

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    post_daily_forecast.start()

# Add a command for testing
@bot.command(name="forecast")
async def manual_forecast(ctx):
    forecast = generate_daily_forecast()
    await ctx.send(forecast)

bot.run(DISCORD_TOKEN)
