import discord 
from discord.ext import commands, tasks
import discord.ui 
from discord.ui import View, Button, button
import sqlite3
import mysql.connector
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
MYSQL_HOST = os.getenv('DATABASE_HOST')
MYSQL_PORT = os.getenv('DATABASE_PORT')
MYSQL_USER = os.getenv('DATABASE_USER')
MYSQL_PASSWORD = os.getenv('DATABASE_PASSWORD')
MYSQL_DATABASE = os.getenv('DATABASE_NAME')
if not all([MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]):
    raise ValueError("❌ Database credentials not found. Please set them in your .env file.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize bot intents
intents = discord.Intents.default()
intents.message_content = True

# Custom help command class
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
            "⚙️ Utility": ["ping", "menu", "cleanup_database"]
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

# Initialize bot with custom help - do this only once
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
    "winter": {"temp_range": (30, 50), "weather_types": ["snowy", "cold", "windy", "foggy"]}
}

# Initialize SQLite database
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
    logging.info("Database initialized successfully.")

# Set the timezone to US/Central
def is_dst():
    today = datetime.now()
    dst_start = datetime(today.year, 3, 8) + timedelta(days=(6 - datetime(today.year, 3, 8).weekday()))
    dst_end = datetime(today.year, 11, 1) + timedelta(days=(6 - datetime(today.year, 11, 1).weekday()))
    return dst_start <= today < dst_end

def get_timezone_offset():
    return timedelta(hours=-5) if is_dst() else timedelta(hours=-6)

# Button and View classes
class MainMenuView(View):
    def __init__(self, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.server_id = ctx.guild.id

    @button(label="📖 Read Weather", style=discord.ButtonStyle.primary)
    async def read_weather_btn(self, interaction: discord.Interaction, button: Button):
        # Instead of calling the command directly, respond with the same logic
        server_id = interaction.guild.id
        now = datetime.now()
        
        # Get today and tomorrow's dates
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Use DISTINCT to ensure we only get one entry per date
        query = '''
            SELECT DISTINCT forecast_date, forecast_text
            FROM weather_forecast
            WHERE server_id=? AND forecast_date IN (?, ?)
            ORDER BY forecast_date
        '''
        result = db_execute(query, (server_id, today, tomorrow), fetchall=True)

        if result:
            forecast_lines = [
                f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n{row[1]}"
                for row in result
            ]
            await interaction.response.send_message(f"🌦️ **Current Weather Reading**:\n\n" + "\n\n".join(forecast_lines))
        else:
            await interaction.response.send_message("⚠️ No current forecast available for today or tomorrow.")

    @button(label="📅 7-Day Forecast", style=discord.ButtonStyle.primary)
    async def view_forecast_btn(self, interaction: discord.Interaction, button: Button):
        server_id = interaction.guild.id
        start_date = datetime.now()
        
        date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        # Use DISTINCT to ensure we only get one entry per date
        placeholders = ",".join("?" for _ in date_list)
        query = f'''
            SELECT DISTINCT forecast_date, forecast_text
            FROM weather_forecast
            WHERE server_id=? AND forecast_date IN ({placeholders})
            ORDER BY forecast_date
        '''
        result = db_execute(query, (server_id, *date_list), fetchall=True)

        if result:
            forecast_lines = [
                f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n{row[1]}"
                for row in result
            ]
            await interaction.response.send_message(f"🌤 **7-Day Forecast**:\n\n" + "\n\n".join(forecast_lines))
        else:
            await interaction.response.send_message("⚠️ No forecast data found for the upcoming 7 days.")

    @button(label="🔮 Generate Forecast", style=discord.ButtonStyle.secondary)
    async def generate_forecast_btn(self, interaction: discord.Interaction, button: Button):
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not any(role.name.lower() == "admin" for role in interaction.user.roles):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
            
        server_id = interaction.guild.id
        current_date = datetime.now()
        season = "spring"  # You can determine the season based on the current date

        for day in range(1, 8):  # Generate forecast for the next 7 days
            forecast_date = (current_date + timedelta(days=day)).strftime("%Y-%m-%d")
            forecast_text = generate_daily_forecast(season, "coastal")

            # Insert the forecast into the database
            db_execute(
                '''INSERT INTO weather_forecast (server_id, forecast_date, forecast_text) VALUES (?, ?, ?)''',
                (server_id, forecast_date, forecast_text)
            )

        await interaction.response.send_message("📅 One-week forecast generated.")

    @button(label="📌 Set Weather Channel", style=discord.ButtonStyle.success)
    async def set_channel_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Use `!set_weather_channel #channel` directly.", ephemeral=True)

    @button(label="📺 Show Weather Channel", style=discord.ButtonStyle.success)
    async def show_channel_btn(self, interaction: discord.Interaction, button: Button):
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not any(role.name.lower() == "admin" for role in interaction.user.roles):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
            
        result = db_execute('''SELECT weather_channel_id FROM server_settings WHERE server_id=?''', (interaction.guild.id,), fetchone=True)
        if result and (channel := interaction.client.get_channel(result[0])):
            await interaction.response.send_message(f"📌 Current weather channel: {channel.mention}")
        else:
            await interaction.response.send_message("❌ No weather channel set! Use `!set_weather_channel`")

    @button(label="🏓 Ping", style=discord.ButtonStyle.secondary)
    async def ping_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🏓 Pong!", ephemeral=True)

# Generate base weather
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

# Generate daily forecast
def generate_daily_forecast(season, location):
    weather_type, temperature = generate_base_weather(season, location)
    return f"{weather_type} and {temperature}°F"

def db_execute(query, params=(), fetchone=False, fetchall=False):
    try:
        with sqlite3.connect('weather_bot.db') as conn:
            c = conn.cursor()
            logging.info(f"Executing query: {query} with params: {params}")
            c.execute(query, params)
            if fetchone:
                return c.fetchone()
            if fetchall:
                return c.fetchall()
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator or any(role.name.lower() == "admin" for role in ctx.author.roles)

# Help commands
@bot.command(name="menu") #Display menu buttons
async def menu(ctx):
    """Show interactive weather system menu."""
    view = MainMenuView(ctx)
    await ctx.send("🧭 **Kyonin Weather System Menu**", view=view)

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

def format_golarion_date(date_obj: datetime) -> str:
    """Return a lore-friendly Golarion date string like 'Oathday, Pharast 10'."""
    golarion_days = [
        "Sunday", "Moonday", "Toilday", "Wealday", "Oathday", "Fireday", "Starday"
    ]
    golarion_months = [
        "Abadius", "Calistril", "Pharast", "Gozran", "Desnus", "Sarenith",
        "Erastus", "Arodus", "Rova", "Lamashan", "Neth", "Kuthona"
    ]
    weekday = golarion_days[date_obj.weekday()]
    month = golarion_months[date_obj.month - 1]
    return f"{weekday}, {month} {date_obj.day}"

@bot.command(name="view_forecast")
async def view_forecast(ctx, *, date: str = None):
    """View the 7-day forecast starting from today or a specific date."""
    server_id = ctx.guild.id

    if date:
        try:
            start_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Please use the format YYYY-MM-DD for the date.")
            return
    else:
        start_date = datetime.now()

    date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # Debug logging - check what dates we're querying
    logging.info(f"Querying forecast for dates: {date_list}")

    # Use DISTINCT to ensure we only get one entry per date
    placeholders = ",".join("?" for _ in date_list)
    query = f'''
        SELECT DISTINCT forecast_date, forecast_text
        FROM weather_forecast
        WHERE server_id=? AND forecast_date IN ({placeholders})
        ORDER BY forecast_date
    '''
    result = db_execute(query, (server_id, *date_list), fetchall=True)

    # Debug logging - check how many results we got
    logging.info(f"Retrieved {len(result) if result else 0} forecast entries")

    if result:
        forecast_lines = [
            f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n{row[1]}"
            for row in result
        ]
        await ctx.send(f"🌤 **7-Day Forecast**:\n\n" + "\n\n".join(forecast_lines))
    else:
        await ctx.send("⚠️ No forecast data found for the upcoming 7 days.")

# Admin command to manually post today's weather update
@bot.command(name="post_weather")
async def post_weather(ctx):
    """Admin command to manually post today's weather update."""
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    
    server_id = ctx.guild.id
    
    # Get the configured weather channel
    result = db_execute(
        '''SELECT weather_channel_id FROM server_settings WHERE server_id=?''',
        (server_id,), fetchone=True
    )
    
    if not result:
        await ctx.send("❌ No weather channel has been configured. Use `!set_weather_channel` first.")
        return
        
    channel_id = result[0]
    channel = bot.get_channel(channel_id)
    
    if not channel:
        await ctx.send(f"❌ Could not find the configured weather channel. Please use `!set_weather_channel` to set a new one.")
        return
    
    # Get current time in Central timezone
    central = pytz.timezone("US/Central")
    now = datetime.now(central)
    today_date = now.strftime("%Y-%m-%d")
    golarion_date = format_golarion_date(now)
    
    # Get today's forecast
    forecast = db_execute(
        '''SELECT forecast_text FROM weather_forecast 
           WHERE server_id=? AND forecast_date=?''',
        (server_id, today_date), fetchone=True
    )
    
    try:
        if forecast:
            await channel.send(f"📅 **Weather for {golarion_date}**\n{forecast[0]}")
            await ctx.send(f"✅ Weather update for today has been posted to {channel.mention}")
        else:
            await ctx.send(f"⚠️ No forecast found for today ({today_date}). Generate a forecast first with `!generate_forecast`.")
    except discord.errors.Forbidden:
        await ctx.send(f"❌ Missing permissions to post in {channel.mention}.")
    except Exception as e:
        await ctx.send(f"❌ Error posting forecast: {str(e)}")
        logging.error(f"Failed to manually post forecast: {e}")

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

@bot.command(name="read_weather")
async def read_weather(ctx):
    """Read today's and tomorrow's weather."""
    server_id = ctx.guild.id
    now = datetime.now()
    
    # Get today and tomorrow's dates
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Debug logging
    logging.info(f"Reading weather for today ({today}) and tomorrow ({tomorrow})")
    
    # Use DISTINCT to ensure we only get one entry per date
    query = '''
        SELECT DISTINCT forecast_date, forecast_text
        FROM weather_forecast
        WHERE server_id=? AND forecast_date IN (?, ?)
        ORDER BY forecast_date
    '''
    result = db_execute(query, (server_id, today, tomorrow), fetchall=True)
    
    # Debug logging
    logging.info(f"Retrieved {len(result) if result else 0} weather entries")

    if result:
        forecast_lines = [
            f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n{row[1]}"
            for row in result
        ]
        await ctx.send(f"🌦️ **Current Weather Reading**:\n\n" + "\n\n".join(forecast_lines))
    else:
        await ctx.send("⚠️ No current forecast available for today or tomorrow.")

# Admin command to clean up duplicate entries
@bot.command(name="cleanup_database")
async def cleanup_database(ctx):
    """Admin command to clean up duplicate forecast entries."""
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
        
    server_id = ctx.guild.id
    
    # Get count before cleanup
    count_before = db_execute(
        '''SELECT COUNT(*) FROM weather_forecast WHERE server_id=?''', 
        (server_id,), fetchone=True
    )[0]
    
    # Delete duplicate entries, keeping only one entry per server_id and forecast_date
    cleanup_query = '''
    DELETE FROM weather_forecast 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM weather_forecast 
        WHERE server_id = ?
        GROUP BY server_id, forecast_date
    ) AND server_id = ?
    '''
    
    db_execute(cleanup_query, (server_id, server_id))
    
    # Get count after cleanup
    count_after = db_execute(
        '''SELECT COUNT(*) FROM weather_forecast WHERE server_id=?''', 
        (server_id,), fetchone=True
    )[0]
    
    removed = count_before - count_after
    await ctx.send(f"🧹 Database cleanup complete. Removed {removed} duplicate entries.")
    logging.info(f"Database cleanup for server {server_id}: removed {removed} duplicates")

@bot.command(name="ping") # Simple ping command to ensure bot is responsive.
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Daily weather posting task
@tasks.loop(minutes=15)
async def post_daily_weather():
    try:
        # Get current time in Central timezone
        central = pytz.timezone("US/Central")
        now = datetime.now(central)
        logging.info(f"Current time: {now}")

        # Check if it's between midnight and 15 minutes after
        # This ensures we don't miss the window between function calls
        if now.hour == 0 and now.minute < 15:
            logging.info("Midnight window detected - posting daily weather")
            
            # Format today's date in SQL format
            today_date = now.strftime("%Y-%m-%d")
            golarion_date = format_golarion_date(now)
            
            for guild in bot.guilds:
                result = db_execute(
                    '''SELECT weather_channel_id FROM server_settings WHERE server_id=?''',
                    (guild.id,), fetchone=True
                )
                if not result:
                    logging.info(f"No weather channel configured for guild {guild.id}")
                    continue
                    
                channel_id = result[0]
                channel = bot.get_channel(channel_id)
                
                if not channel:
                    logging.warning(f"Could not find channel with ID {channel_id} for guild {guild.id}")
                    continue
                
                # Get today's forecast using the explicit date
                forecast = db_execute(
                    '''SELECT forecast_text FROM weather_forecast 
                       WHERE server_id=? AND forecast_date=?''',
                    (guild.id, today_date), fetchone=True
                )
                
                try:
                    if forecast:
                        await channel.send(f"📅 **Weather for {golarion_date}**\n{forecast[0]}")
                        logging.info(f"Posted weather for {guild.name}")
                    else:
                        await channel.send(f"📅 **Weather for {golarion_date}**\n⚠️ No forecast available.")
                        logging.warning(f"No forecast found for guild {guild.id} on {today_date}")
                except discord.errors.Forbidden:
                    logging.error(f"Missing permissions to post in channel {channel.name} in guild {guild.name}")
                except Exception as e:
                    logging.error(f"Failed to post forecast to {guild.name}: {e}")
    except Exception as e:
        logging.error(f"Error in post_daily_weather task: {e}")
        # Don't let the task die - it will continue with the next scheduled run

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    initialize_database()
    if not post_daily_weather.is_running():
        post_daily_weather.start()

if TOKEN:
    bot.run(TOKEN)