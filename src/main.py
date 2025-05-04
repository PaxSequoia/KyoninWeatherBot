import discord
from discord.ext import commands, tasks
import sqlite3
import random
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta, time, timezone
import pytz

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found. Please set it in your .env file.")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize bot intents
intents = discord.Intents.default()
intents.message_content = True

class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.bot = None

    async def send_bot_help(self, mapping):
        self.bot = self.context.bot
        embed = discord.Embed(
            title="🌦️ Kingdom of Kyonin Weather System",
            description="**Version 1.0.3-secure**\nComplete Command Reference",
            color=0x3498db
        )

        categories = {
            "📌 Channel Management": ["set_weather_channel", "show_weather_channel"],
            "🗕️ Forecast Control": ["generate_forecast", "view_forecast"],
            "👥 Role Settings": ["set_weather_reader_role", "view_weather_reader_role"],
            "👁️ Preview": ["read_weather"],
            "⚙️ Utility": ["ping"]
        }

        for category, command_names in categories.items():
            cmd_list = []
            for name in command_names:
                cmd = self.bot.get_command(name)
                if cmd and not cmd.hidden:
                    help_text = cmd.short_doc or "No description available"
                    cmd_list.append(f"• `!{cmd.name}` - {help_text}")

            if cmd_list:
                embed.add_field(
                    name=category,
                    value="\n".join(cmd_list),
                    inline=False
                )

        await self.get_destination().send(embed=embed)

# Initialize bot with custom help
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=CustomHelpCommand()
)

# Constants
GOLARION_DAYS = ["Moonday", "Toilday", "Wealday", "Oathday", "Fireday", "Starday", "Sunday"]
SEASONS = {
    "spring": {"temp_range": (50, 70), "weather_types": ["sunny", "rainy", "cloudy", "misty"]},
    "summer": {"temp_range": (75, 95), "weather_types": ["sunny", "stormy", "humid", "foggy"]},
    "autumn": {"temp_range": (45, 65), "weather_types": ["cloudy", "windy", "rainy", "misty"]},
    "winter": {"temp_range": (20, 40), "weather_types": ["snowy", "cold", "cloudy", "foggy"]}
}

# Helper functions
def is_dst():
    today = datetime.now()
    dst_start = datetime(today.year, 3, 8) + timedelta(days=(6 - datetime(today.year, 3, 8).weekday()))
    dst_end = datetime(today.year, 11, 1) + timedelta(days=(6 - datetime(today.year, 11, 1).weekday()))
    return dst_start <= today < dst_end

def get_timezone_offset():
    return timedelta(hours=-5) if is_dst() else timedelta(hours=-6)

def generate_base_weather(season, location):
    config = SEASONS[season]
    temp_range = config["temp_range"]
    weather_types = config["weather_types"].copy()

    modifier = -5 if location == "coastal" else -3
    temp_range = (temp_range[0] + modifier, temp_range[1] + modifier)

    if location == "coastal":
        weather_types += ["stormy", "humid"] * 3
    elif location == "forest":
        weather_types += ["foggy", "misty"] * 2

    return random.choice(weather_types), random.randint(temp_range[0], temp_range[1])

def generate_daily_forecast(season, location):
    weather_type, temperature = generate_base_weather(season, location)
    return f"{weather_type} and {temperature}°F"

def db_execute(query, params=(), fetchone=False, fetchall=False):
    try:
        with sqlite3.connect('weather_bot.db') as conn:
            c = conn.cursor()
            c.execute(query, params)
            if fetchone:
                return c.fetchone()
            if fetchall:
                return c.fetchall()
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None

def initialize_database():
    with sqlite3.connect('weather_bot.db') as conn:
        c = conn.cursor()
        # Create server_settings table
        c.execute('''CREATE TABLE IF NOT EXISTS server_settings (
                    server_id INTEGER PRIMARY KEY,
                    weather_channel_id INTEGER)''')

        # Create weather_forecast table
        c.execute('''CREATE TABLE IF NOT EXISTS weather_forecast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    forecast_date TEXT NOT NULL,
                    forecast_text TEXT NOT NULL)''')

        conn.commit()

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator or any(role.name.lower() == "admin" for role in ctx.author.roles)

@bot.command(name="set_weather_channel")
async def set_weather_channel(ctx, channel: discord.TextChannel):
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    db_execute('''INSERT OR REPLACE INTO server_settings (server_id, weather_channel_id) VALUES (?, ?)''', (ctx.guild.id, channel.id))
    await ctx.send(f"🌊 Weather updates will be posted in {channel.mention}")

@bot.command(name="show_weather_channel")
async def show_weather_channel(ctx):
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    result = db_execute('''SELECT weather_channel_id FROM server_settings WHERE server_id=?''', (ctx.guild.id,), fetchone=True)
    if result and (channel := bot.get_channel(result[0])):
        await ctx.send(f"📌 Current weather channel: {channel.mention}")
    else:
        await ctx.send("❌ No weather channel set! Use `!set_weather_channel`")

@bot.command(name="generate_forecast")
async def generate_forecast(ctx):
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    server_id = ctx.guild.id
    current_date = datetime.now()
    season = "spring"  # You can determine the season based on the current date

    for day in range(1, 8):  # Generate forecast for the next 7 days
        forecast_date = (current_date + timedelta(days=day)).strftime("%Y-%m-%d")
        forecast_text = generate_daily_forecast(season, "coastal")  # You can change "coastal" to any location

        # Insert the forecast into the database
        db_execute(
            '''INSERT INTO weather_forecast (server_id, forecast_date, forecast_text) VALUES (?, ?, ?)''',
            (server_id, forecast_date, forecast_text)
        )

        # Log the inserted data
        logging.info(f"Generated forecast for server {server_id} on {forecast_date}: {forecast_text}")

    await ctx.send("📅 One-week forecast generated.")

@bot.command(name="view_forecast")
async def view_forecast(ctx, *, date: str = None):
    """View the forecast for a specific date."""
    server_id = ctx.guild.id

    if date:
        forecast_date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
    else:
        forecast_date = datetime.now().strftime("%Y-%m-%d")

    # Retrieve the forecast from the database
    result = db_execute(
        '''SELECT forecast_text FROM weather_forecast WHERE server_id=? AND forecast_date=?''',
        (server_id, forecast_date), fetchone=True
    )

    # Log the retrieved data
    if result:
        logging.info(f"Retrieved forecast for server {server_id} on {forecast_date}: {result[0]}")
        await ctx.send(f"📅 **Forecast for {forecast_date}**\n{result[0]}")
    else:
        logging.warning(f"No forecast found for server {server_id} on {forecast_date}.")
        await ctx.send(f"⚠️ No forecast available for {forecast_date}.")

@bot.command(name="set_weather_reader_role")
async def set_weather_reader_role(ctx, role: discord.Role):
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    await ctx.send(f"👥 Reader role set to: {role.name}")  # Placeholder

@bot.command(name="view_weather_reader_role")
async def view_weather_reader_role(ctx):
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    await ctx.send("👥 Current reader role: Admin")  # Placeholder

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("🏓 Pong!")

@tasks.loop(minutes=15)
async def post_daily_weather():
    central = pytz.timezone("US/Central")
    now = datetime.now(central)
    logging.info(f"Current time: {now}")

    def get_next_midnight_central():
        """Calculate the next midnight in Central Time."""
        now = datetime.now(central)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_midnight

    target_time = get_next_midnight_central()
    logging.info(f"Target time: {target_time}")

    if now.replace(second=0, microsecond=0) == target_time.replace(second=0, microsecond=0):
        for guild in bot.guilds:
            result = db_execute(
                '''SELECT weather_channel_id FROM server_settings WHERE server_id=?''',
                (guild.id,), fetchone=True
            )
            if not result:
                continue
            channel = bot.get_channel(result[0])
            if channel:
                today = datetime.now().strftime("%A, %B %d")
                forecast = db_execute(
                    '''SELECT forecast_text FROM weather_forecast WHERE server_id=? AND forecast_date=date("now", "localtime")''',
                    (guild.id,), fetchone=True
                )
                try:
                    if forecast:
                        await channel.send(f"📅 **Weather for {today}**\n{forecast[0]}")
                    else:
                        await channel.send(f"📅 **Weather for {today}**\n⚠️ No forecast available.")
                except Exception as e:
                    logging.error(f"Failed to post forecast to {guild.name}: {e}")

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    initialize_database()
    if not post_daily_weather.is_running():
        post_daily_weather.start()

if TOKEN:
    bot.run(TOKEN)