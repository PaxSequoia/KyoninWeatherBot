import discord 
from discord.ext import commands, tasks
import discord.ui 
from discord.ui import View, Button, button
import sqlite3
# import mysql.connector # Removed MySQL import
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
# MYSQL_HOST = os.getenv('DATABASE_HOST') # Removed MySQL config
# MYSQL_PORT = os.getenv('DATABASE_PORT') # Removed MySQL config
# MYSQL_USER = os.getenv('DATABASE_USER') # Removed MySQL config
# MYSQL_PASSWORD = os.getenv('DATABASE_PASSWORD') # Removed MySQL config
# MYSQL_DATABASE = os.getenv('DATABASE_NAME') # Removed MySQL config
# if not all([MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]): # Removed MySQL config check
    # raise ValueError("❌ Database credentials not found. Please set them in your .env file.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize bot intents
intents = discord.Intents.default()
intents.message_content = True

# Import from weather_generator
from weather_generator import get_simple_forecast as get_advanced_simple_forecast

# Custom help command class
class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.bot = None

    async def send_bot_help(self, mapping):
        self.bot = self.context.bot
        embed = discord.Embed(
            title="🌦️ Kingdom of Kyonin Weather System",
            description="**Version 1.0.4-secure**\nComplete Command Reference",
            color=0x3498db
        )

        categories = {
            "📌 Channel Management": ["set_weather_channel", "show_weather_channel"],
            "🗕️ Forecast Control": [
                "generate_forecast", "view_forecast", "post_weather",
                "archive_week", "historic_forecast"  # <-- Added archive commands here
            ],
            "👥 Role Settings": ["set_weather_reader_role", "view_weather_reader_role"],
            "👁️ Preview": ["read_weather"],
            "⚙️ Utility": ["ping", "menu", "cleanup_database", "weather_help", "analyze_weather_trends"]
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
    help_command=None  # We'll register our help command manually
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
                    weather_channel_id INTEGER,
                    weather_reader_role TEXT)''') # Added weather_reader_role

        # Create weather_forecast table
        c.execute('''CREATE TABLE IF NOT EXISTS weather_forecast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    forecast_date TEXT NOT NULL,
                    coastal_forecast_text TEXT NOT NULL,  -- Renamed from forecast_text
                    forest_forecast_text TEXT NOT NULL,   -- Added forest_forecast_text
                    UNIQUE(server_id, forecast_date))''') # Added UNIQUE constraint

        # Create weekly_forecast_archive table
        c.execute('''CREATE TABLE IF NOT EXISTS weekly_forecast_archive (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id INTEGER NOT NULL,
                        week_start_date TEXT NOT NULL,
                        week_end_date TEXT NOT NULL,
                        forecasts TEXT NOT NULL
                    )''')
        conn.commit()
    logging.info("Database initialized successfully.")

# Helper function to get current season (from Weather_0.0.1b.py)
# Note: SEASONS dict in main.py is simpler and used by this for determining the season string.
# weather_generator.py has SEASONS_EXTENDED for its internal detailed logic. This is fine.
def get_current_season():
    """Determine the current season based on the real-world date."""
    # This is a simplified version. Golarion seasons are complex.
    today = datetime.now()
    month = today.month
    if month in [12, 1, 2]: # Assuming Northern Hemisphere mapping for Golarion months
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "autumn"

# Button and View classes
class MainMenuView(View):
    def __init__(self, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.server_id = ctx.guild.id

    @button(label="📖 Read Weather", style=discord.ButtonStyle.primary)
    async def read_weather_btn(self, interaction: discord.Interaction, button: Button):
        # Permission check for reading weather
        if not await can_read_weather(interaction): # Use the new helper
            await interaction.response.send_message("❌ You don't have permission to read the weather forecast.", ephemeral=True)
            return

        server_id = interaction.guild.id
        now = datetime.now()
        
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Query for coastal and forest forecasts
        query = '''
            SELECT forecast_date, coastal_forecast_text, forest_forecast_text
            FROM weather_forecast
            WHERE server_id=? AND forecast_date IN (?, ?)
            ORDER BY forecast_date
        '''
        # No DISTINCT needed due to UNIQUE constraint on (server_id, forecast_date)
        result = db_execute(query, (server_id, today, tomorrow), fetchall=True)

        if result:
            forecast_lines = [
                f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n" # Date
                f"  🌊 Coastal: {row[1]}\n"  # Coastal forecast
                f"  🌳 Forest: {row[2]}"     # Forest forecast
                for row in result
            ]
            # Send message ephemerally for button clicks to avoid cluttering channel
            await interaction.response.send_message(f"🌦️ **Current Weather Reading**:\n\n" + "\n\n".join(forecast_lines), ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No current forecast available for today or tomorrow.", ephemeral=True)

    @button(label="📅 7-Day Forecast", style=discord.ButtonStyle.primary)
    async def view_forecast_btn(self, interaction: discord.Interaction, button: Button):
        # Permission check (though viewing forecast is generally less sensitive, good for consistency)
        if not await can_read_weather(interaction):
             await interaction.response.send_message("❌ You don't have permission to view the forecast.", ephemeral=True)
             return

        server_id = interaction.guild.id
        start_date = datetime.now()
        
        date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        placeholders = ",".join("?" for _ in date_list)
        query = f'''
            SELECT forecast_date, coastal_forecast_text, forest_forecast_text
            FROM weather_forecast
            WHERE server_id=? AND forecast_date IN ({placeholders})
            ORDER BY forecast_date
        '''
        result = db_execute(query, (server_id, *date_list), fetchall=True)

        if result:
            forecast_lines = [
                f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n"
                f"  🌊 Coastal: {row[1]}\n  🌳 Forest: {row[2]}"
                for row in result
            ]
            await interaction.response.send_message(f"🌤 **7-Day Forecast**:\n\n" + "\n\n".join(forecast_lines), ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No forecast data found for the upcoming 7 days.", ephemeral=True)

    @button(label="🔮 Generate Forecast", style=discord.ButtonStyle.secondary)
    async def generate_forecast_btn(self, interaction: discord.Interaction, button: Button):
        # Check admin permissions using the helper
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
            
        server_id = interaction.guild.id
        
        # Archive current week's forecast before generating new one
        archive_success = archive_weekly_forecast(server_id)
        archive_message = "📦 Previous week's forecast archived. " if archive_success else "ℹ️ No previous week's forecast to archive. "

        current_date = datetime.now()
        season = get_current_season() # Use helper to get current season

        for day_offset in range(7):  # Generate for today and next 6 days
            forecast_date = (current_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            # Call new generate_daily_forecast for each region
            coastal_f = generate_daily_forecast(region="coastal", season=season)
            forest_f = generate_daily_forecast(region="forest", season=season)

            # Insert or replace the dual forecast into the database
            db_execute(
                '''INSERT OR REPLACE INTO weather_forecast 
                   (server_id, forecast_date, coastal_forecast_text, forest_forecast_text) 
                   VALUES (?, ?, ?, ?)''',
                (server_id, forecast_date, coastal_f, forest_f)
            )

        await interaction.response.send_message(f"{archive_message}📅 New 7-day forecast (Coastal & Forest) generated using advanced generator.", ephemeral=True)

    @button(label="📤 Post Weather", style=discord.ButtonStyle.danger)
    async def post_weather_btn(self, interaction: discord.Interaction, button: Button):
        # Check admin permissions using the helper
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
            
        server_id = interaction.guild.id
        
        # Get the configured weather channel
        result = db_execute(
            '''SELECT weather_channel_id FROM server_settings WHERE server_id=?''',
            (server_id,), fetchone=True
        )
        
        if not result:
            await interaction.response.send_message("❌ No weather channel has been configured. Use `!set_weather_channel` first.")
            return
            
        channel_id = result[0]
        channel = interaction.client.get_channel(channel_id)
        
        if not channel:
            await interaction.response.send_message(f"❌ Could not find the configured weather channel. Please use `!set_weather_channel` to set a new one.")
            return
        
        # Get current time in Central timezone
        central = pytz.timezone("US/Central")
        now = datetime.now(central)
        today_date = now.strftime("%Y-%m-%d")
        
        # Get Golarion day name for today
        golarion_day = GOLARION_DAYS[now.weekday()]
        
        # Get today's forecast (coastal and forest)
        forecast_data = db_execute(
            '''SELECT coastal_forecast_text, forest_forecast_text FROM weather_forecast 
               WHERE server_id=? AND forecast_date=?''',
            (server_id, today_date), fetchone=True
        )
        
        try:
            if forecast_data:
                coastal_forecast, forest_forecast = forecast_data
                                
                # Format the message
                weather_message = f"\n**Daily Weather Report ({golarion_day})** \n"
                weather_message += f"• Coastal Region: {coastal_forecast}\n" # Corrected newline
                weather_message += f"• Fiereni Forest: {forest_forecast}\n" # Corrected newline
                weather_message += "*May the winds favor your travels!*"
                
                await channel.send(weather_message)
                await interaction.response.send_message(f"✅ Weather update for today has been manually posted to {channel.mention}")
            else:
                await interaction.response.send_message(f"⚠️ No forecast found for today ({today_date}). Generate a forecast first!")
        except discord.errors.Forbidden:
            await interaction.response.send_message(f"❌ Missing permissions to post in {channel.mention}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error posting forecast: {str(e)}")
            logging.error(f"Failed to manually post forecast: {e}")

    @button(label="📌 Set Weather Channel", style=discord.ButtonStyle.success)
    async def set_channel_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Use `!set_weather_channel #channel` directly.", ephemeral=True)

    @button(label="📺 Show Weather Channel", style=discord.ButtonStyle.success)
    async def show_channel_btn(self, interaction: discord.Interaction, button: Button):
        # Check admin permissions using the helper
        if not is_admin(interaction):
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

# Help command
@bot.command(name="weather_help")
async def weather_help(ctx):
    """Show this help message."""
    help_command = CustomHelpCommand()
    help_command.context = await bot.get_context(ctx.message)
    await help_command.send_bot_help(bot.all_commands)

# Updated generate_daily_forecast in src/main.py to use weather_generator
# This function will now be called PER REGION.
# Trend probabilities are no longer passed here as weather_generator.py's get_simple_forecast doesn't use them.
def generate_daily_forecast(region: str, season: str): 
    """
    Generates a daily forecast string for a specific region and season
    using the advanced weather generator.
    """
    # weather_generator's get_simple_forecast is aliased to get_advanced_simple_forecast
    # It takes: season, region, days=1, style="brief" (default in weather_generator)
    # We'll use style="standard" for a good level of detail as per task example.
    forecast_text = get_advanced_simple_forecast(season=season, region=region, days=1, style="standard")
    return forecast_text

def db_execute(query, params=(), fetchone=False, fetchall=False):
    """
    Executes a given SQL query with specified parameters.
    The connection implicitly handles commits on success or rollbacks on error
    when using the 'with' statement for data manipulation queries (INSERT, UPDATE, DELETE).

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters to substitute into the query. Defaults to ().
        fetchone (bool, optional): True if the query should fetch one row. Defaults to False.
        fetchall (bool, optional): True if the query should fetch all rows. Defaults to False.

    Returns:
        Optional[Any]: Query result if fetchone or fetchall is True. 
                       For INSERT/UPDATE/DELETE, returns None if successful.
                       Returns None on database error.
    """
    try:
        with sqlite3.connect('weather_bot.db') as conn:
            c = conn.cursor()
            # Changed to debug for less noise during normal operations
            logging.debug(f"Executing query: {query} with params: {params}") 
            c.execute(query, params)
            if fetchone:
                return c.fetchone()
            if fetchall:
                return c.fetchall()
            # For INSERT, UPDATE, DELETE, the 'with' statement handles commit on success.
            # No explicit conn.commit() is needed here for single statements.
    except sqlite3.Error as e:
        # Log the specific query and params that caused the error
        logging.error(f"Database error executing query '{query}' with params {params}: {e}")
        return None
    
# Archive weekly forecast
def archive_weekly_forecast(server_id):
    """Archive the current week's forecast for the server."""
    today = datetime.now()
    # Find the most recent Monday (start of week)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    placeholders = ",".join("?" for _ in week_dates)
    query = f'''
        SELECT forecast_date, coastal_forecast_text, forest_forecast_text
        FROM weather_forecast
        WHERE server_id=? AND forecast_date IN ({placeholders})
        ORDER BY forecast_date
    '''
    result = db_execute(query, (server_id, *week_dates), fetchall=True) # Fetches (date, coastal, forest)
    if result:
        # Store with both forecasts, formatted for readability
        forecasts_details = []
        for row_date, coastal_text, forest_text in result:
            forecasts_details.append(f"📅 **{format_golarion_date(datetime.strptime(row_date, '%Y-%m-%d'))}**\n"
                                     f"  🌊 Coastal: {coastal_text}\n"
                                     f"  🌳 Forest: {forest_text}")
        forecasts_str = "\n\n".join(forecasts_details) # Double newline between daily entries
        
        # Using INSERT OR REPLACE for archive entries to prevent duplicates if run multiple times for same week.
        db_execute(
            '''INSERT OR REPLACE INTO weekly_forecast_archive (server_id, week_start_date, week_end_date, forecasts)
               VALUES (?, ?, ?, ?)''',
            (server_id, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"), forecasts_str)
        )
        logging.info(f"Archived weekly forecast for server {server_id} ({week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')})")
        return True
    return False

# Check if the user is an admin
def is_admin(ctx_or_interaction):
    """Checks if the user is an admin, works for both Context and Interaction."""
    user = None
    if isinstance(ctx_or_interaction, commands.Context):
        user = ctx_or_interaction.author
    elif isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
    
    if user and hasattr(user, 'guild_permissions'): # Check if user object is valid and has guild_permissions
        # guild_permissions might be None in DMs, but admin commands are guild-only anyway
        if user.guild_permissions:
            return user.guild_permissions.administrator or any(role.name.lower() == "admin" for role in user.roles)
    return False

# Helper function to check if user can read weather (admin or has reader role)
async def can_read_weather(ctx_or_interaction):
    """Checks if the user can read weather. True if admin, or if they have the 'weather_reader_role', or if no role is set."""
    if is_admin(ctx_or_interaction):
        return True
    
    guild_id = None
    user_roles = None

    if isinstance(ctx_or_interaction, commands.Context):
        if not ctx_or_interaction.guild: return False # DM context
        guild_id = ctx_or_interaction.guild.id
        user_roles = ctx_or_interaction.author.roles
    elif isinstance(ctx_or_interaction, discord.Interaction):
        if not ctx_or_interaction.guild: return False # Should not happen with guild commands
        guild_id = ctx_or_interaction.guild.id
        user_roles = ctx_or_interaction.user.roles
        
    if not guild_id or not user_roles: # Should not be reached if checks above are fine
        return False

    settings = db_execute("SELECT weather_reader_role FROM server_settings WHERE server_id = ?", (guild_id,), fetchone=True)
    if settings and settings[0]: # A specific reader role is set
        reader_role_name = settings[0]
        return any(role.name == reader_role_name for role in user_roles)
    
    # If no reader role is set in DB, default to allowing everyone.
    # Change to 'return False' here to restrict to admin only if no role is set.
    return True

# Admin Command to archive the weekly forecast
@bot.command(name="archive_week")
async def archive_week(ctx):
    """Archive this week's forecast (admin only)."""
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    success = archive_weekly_forecast(ctx.guild.id)
    if success:
        await ctx.send("📦 This week's forecast has been archived.")
    else:
        await ctx.send("⚠️ No forecast data found for this week to archive.")

#Command to view archived forecasts
@bot.command(name="historic_forecast")
async def historic_forecast(ctx, week_start: str = None):
    """
    View archived weekly forecasts.
    Usage: !historic_forecast [YYYY-MM-DD]
    If no date is given, shows the most recent archive.
    """
    server_id = ctx.guild.id
    if week_start:
        try:
            datetime.strptime(week_start, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Please use the format YYYY-MM-DD for the week start date.")
            return
        result = db_execute(
            '''SELECT week_start_date, week_end_date, forecasts
               FROM weekly_forecast_archive
               WHERE server_id=? AND week_start_date=?
               ORDER BY week_start_date DESC''',
            (server_id, week_start), fetchone=True
        )
    else:
        result = db_execute(
            '''SELECT week_start_date, week_end_date, forecasts
               FROM weekly_forecast_archive
               WHERE server_id=?
               ORDER BY week_start_date DESC LIMIT 1''',
            (server_id,), fetchone=True
        )
    if result:
        week_start, week_end, forecasts = result
        await ctx.send(
            f"📚 **Historic Forecast ({week_start} to {week_end})**\n\n{forecasts}"
        )
    else:
        await ctx.send("⚠️ No archived forecast found for that week.")

# Help commands
@bot.command(name="menu") #Display menu buttons
async def menu(ctx):
    """Show interactive weather system menu."""
    view = MainMenuView(ctx)
    await ctx.send("🧭 **Kyonin Weather System Menu**", view=view)

@bot.command(name="set_weather_channel")
async def set_weather_channel(ctx, channel: discord.TextChannel):
    """Sets the channel for daily weather updates. Admin only."""
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    # Preserve existing weather_reader_role if any, similar to how set_weather_reader_role preserves channel
    db_execute("INSERT OR REPLACE INTO server_settings (server_id, weather_channel_id, weather_reader_role) "
               "VALUES (?, ?, (SELECT weather_reader_role FROM server_settings WHERE server_id = ?))",
               (ctx.guild.id, channel.id, ctx.guild.id))
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
async def generate_forecast(ctx, use_trends_str: str = "False"):
    """Generates a new 7-day forecast. Archives previous week.
    Usage: !generate_forecast [True/False] (e.g. !generate_forecast True)"""
    if not is_admin(ctx):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    server_id = ctx.guild.id
    use_trends_param = use_trends_str.lower() == 'true'

    # Archive the current week's forecast before generating a new one
    archived = archive_weekly_forecast(server_id)
    if archived:
        await ctx.send("📦 Previous week's forecast has been archived before generating new data.")
    # else: # Optional: message if nothing to archive
        # await ctx.send("ℹ️ No previous week's forecast found to archive, or already archived.")

    current_date = datetime.now()
    season = get_current_season() 

    trend_info_message = "" # Initialize trend info message
    if use_trends_param:
        # Call the internal helper function to get trend data
        trends_data = await _get_weather_trends_data(server_id, 7) 
        if trends_data and (trends_data.get("coastal") or trends_data.get("forest")):
            # Log the trend data; it's not directly used by get_advanced_simple_forecast
            trend_coastal_probs_log = trends_data.get("coastal") 
            trend_forest_probs_log = trends_data.get("forest")
            trend_info_message = " Trend analysis was performed." # User message updated
            logging.info(f"Trend data fetched for server {server_id}: Coastal: {trend_coastal_probs_log}, Forest: {trend_forest_probs_log}. Note: This data is not directly applied by the new weather_generator.py's get_simple_forecast.")
        else:
            trend_info_message = " No significant historical trends found or an error occurred during analysis."
            logging.info(f"No trend data to log for server {server_id} during forecast generation, or trends_data was None/empty.")
    
    # The new generate_daily_forecast takes (region, season)
    for day_offset in range(7): # Generate for today and next 6 days
        forecast_date = (current_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        coastal_f = generate_daily_forecast(region="coastal", season=season)
        forest_f = generate_daily_forecast(region="forest", season=season)

        # Insert or replace the dual forecast into the database
        db_execute(
            '''INSERT OR REPLACE INTO weather_forecast 
               (server_id, forecast_date, coastal_forecast_text, forest_forecast_text) 
               VALUES (?, ?, ?, ?)''',
            (server_id, forecast_date, coastal_f, forest_f)
        )
        logging.info(f"Generated forecast for server {server_id} on {forecast_date} using advanced generator: Coastal: {coastal_f}, Forest: {forest_f}")

    await ctx.send(f"📅 New 7-day forecast (Coastal & Forest) generated using advanced weather generator.{trend_info_message}")

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

    # No DISTINCT needed due to UNIQUE constraint
    placeholders = ",".join("?" for _ in date_list)
    query = f'''
        SELECT forecast_date, coastal_forecast_text, forest_forecast_text
        FROM weather_forecast
        WHERE server_id=? AND forecast_date IN ({placeholders})
        ORDER BY forecast_date
    '''
    result = db_execute(query, (server_id, *date_list), fetchall=True)

    logging.info(f"Retrieved {len(result) if result else 0} forecast entries for view_forecast by {ctx.author} for dates: {date_list}")

    if result:
        forecast_lines = [
            f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n"
            f"  🌊 Coastal: {row[1]}\n  🌳 Forest: {row[2]}"
            for row in result
        ]
        await ctx.send(f"🌤 **7-Day Forecast**:\n\n" + "\n\n".join(forecast_lines))
    else:
        await ctx.send("⚠️ No forecast data found for the specified period.")

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
    
    # Get Golarion day name for today
    golarion_day = GOLARION_DAYS[now.weekday()]
    
    # Get today's forecast (coastal and forest)
    forecast_data = db_execute(
        '''SELECT coastal_forecast_text, forest_forecast_text FROM weather_forecast 
           WHERE server_id=? AND forecast_date=?''',
        (server_id, today_date), fetchone=True
    )
    
    try:
        if forecast_data:
            coastal_forecast, forest_forecast = forecast_data
            
            # Format the message
            weather_message = f"\n**Daily Weather Report ({golarion_day})** \n"
            weather_message += f"• Coastal Region: {coastal_forecast}\n" # Corrected newline
            weather_message += f"• Fiereni Forest: {forest_forecast}\n" # Corrected newline
            weather_message += "*May the winds favor your travels!*"
            
            await channel.send(weather_message)
            await ctx.send(f"✅ Weather update for today has been posted to {channel.mention}")
        else:
            await ctx.send(f"⚠️ No forecast found for today ({today_date}). Generate a forecast first with `!generate_forecast`.")
    except discord.errors.Forbidden:
        await ctx.send(f"❌ Missing permissions to post in {channel.mention}.")
    except Exception as e:
        await ctx.send(f"❌ Error posting forecast: {str(e)}")
        logging.error(f"Failed to manually post forecast: {e}")

@bot.command(name="set_weather_reader_role")
@commands.has_permissions(administrator=True) # Use built-in check for command permissions
async def set_weather_reader_role(ctx, role: discord.Role):
    """Sets the role allowed to read detailed weather forecasts. Usage: !set_weather_reader_role @RoleName"""
    if not role:
        await ctx.send("❌ Please provide a valid role.")
        return
    
    # Using db_execute which handles its own connection and cursor
    db_execute("INSERT OR REPLACE INTO server_settings (server_id, weather_channel_id, weather_reader_role) "
               "VALUES (?, (SELECT weather_channel_id FROM server_settings WHERE server_id = ?), ?)",
              (ctx.guild.id, ctx.guild.id, role.name))
    # The above query ensures weather_channel_id is preserved if it exists, or sets it to NULL if not.
    # A simpler version if weather_channel_id is guaranteed or okay to be NULL initially:
    # db_execute("INSERT OR REPLACE INTO server_settings (server_id, weather_reader_role) VALUES (?, ?)",
    #           (ctx.guild.id, role.name))
    # For this change, I'll assume the first more robust query or that `server_settings` row is typically present.
    # Let's use a simpler update that assumes the row might exist and only updates/sets the role.
    # This requires the server_id to already be in server_settings, or an INSERT OR IGNORE then UPDATE.
    # The schema has server_id as PRIMARY KEY, so INSERT OR REPLACE is fine.
    
    # Simplified using INSERT OR REPLACE and a subquery to preserve existing weather_channel_id or set to NULL.
    # The server_id is the primary key, so this will update if exists, or insert if not.
    db_execute("INSERT OR REPLACE INTO server_settings (server_id, weather_reader_role, weather_channel_id) "
               "VALUES (?, ?, (SELECT weather_channel_id FROM server_settings WHERE server_id = ?))",
               (ctx.guild.id, role.name, ctx.guild.id))
    # Ensure the change is committed if db_execute doesn't auto-commit on non-selects
    # (db_execute in this project *does* commit for non-selects)

    await ctx.send(f"✅ Weather reader role set to: `{role.name}`.")

@bot.command(name="view_weather_reader_role")
@commands.has_permissions(administrator=True)
async def view_weather_reader_role(ctx):
    """Views the currently set weather reader role."""
    result = db_execute("SELECT weather_reader_role FROM server_settings WHERE server_id = ?", (ctx.guild.id,), fetchone=True)
    if result and result[0]:
        await ctx.send(f"ℹ️ Current weather reader role is: `{result[0]}`.")
    else:
        await ctx.send("ℹ️ No specific weather reader role is currently set. If not set, `!read_weather` access is open to all users (admins always have access).")

async def _get_weather_trends_data(server_id: int, days: int) -> dict | None:
    """
    Core logic for analyzing weather trends.
    Fetches data and returns a dictionary of trend probabilities for coastal and forest.
    Returns None if no data or insufficient data.
    """
    # Query for the last 'days' distinct dates that have entries
    query_recent_distinct_dates = f'''
        SELECT DISTINCT forecast_date 
        FROM weather_forecast 
        WHERE server_id = ? 
        ORDER BY forecast_date DESC 
        LIMIT ?
    '''
    recent_distinct_dates_rows = db_execute(query_recent_distinct_dates, (server_id, days), fetchall=True)
    if not recent_distinct_dates_rows:
        logging.info(f"No historical dates found for trend analysis for server {server_id} for the last {days} distinct forecast days.")
        return None

    actual_dates_to_query = [row[0] for row in recent_distinct_dates_rows]
    placeholders = ",".join("?" for _ in actual_dates_to_query)

    query_historical_data = f'''
        SELECT forecast_date, coastal_forecast_text, forest_forecast_text 
        FROM weather_forecast 
        WHERE server_id = ? AND forecast_date IN ({placeholders})
    '''
    historical_data = db_execute(query_historical_data, (server_id, *actual_dates_to_query), fetchall=True)

    if not historical_data:
        logging.info(f"No historical forecast data found for trend analysis for server {server_id} within selected {len(actual_dates_to_query)} dates.")
        return None

    coastal_trends = {}
    forest_trends = {}
    
    def get_primary_condition(forecast_text): # Helper to extract primary weather condition
        return forecast_text.split(" and ")[0].split(",")[0].strip().lower()

    for _, coastal_weather, forest_weather in historical_data:
        coastal_type = get_primary_condition(coastal_weather)
        forest_type = get_primary_condition(forest_weather)
        
        coastal_trends[coastal_type] = coastal_trends.get(coastal_type, 0) + 1
        forest_trends[forest_type] = forest_trends.get(forest_type, 0) + 1
    
    if not coastal_trends and not forest_trends:
        logging.info(f"Trend analysis for {server_id}: No trend data compiled from {len(historical_data)} historical entries.")
        return None

    total_coastal_entries = sum(coastal_trends.values())
    total_forest_entries = sum(forest_trends.values())

    coastal_trend_probs = {k: v / total_coastal_entries for k, v in coastal_trends.items()} if total_coastal_entries > 0 else {}
    forest_trend_probs = {k: v / total_forest_entries for k, v in forest_trends.items()} if total_forest_entries > 0 else {}
    
    logging.info(f"Trend analysis for {server_id} (last {days} distinct forecast days, {len(historical_data)} entries): Coastal: {coastal_trend_probs}, Forest: {forest_trend_probs}")
    return {"coastal": coastal_trend_probs, "forest": forest_trend_probs, "analyzed_entry_count": len(historical_data), "days_span": len(actual_dates_to_query)}

@bot.command(name="analyze_weather_trends")
@commands.has_permissions(administrator=True)
async def analyze_weather_trends(ctx, days: int = 7):
    """Analyzes weather trends using data from the last N distinct forecast days.
    Usage: !analyze_weather_trends [number_of_days] (default is 7)
    """
    if days <= 0:
        await ctx.send("⚠️ Please provide a positive number of days for analysis.")
        return

    server_id = ctx.guild.id
    trend_data = await _get_weather_trends_data(server_id, days)

    if not trend_data or (not trend_data.get("coastal") and not trend_data.get("forest")):
        await ctx.send(f"📉 No significant historical weather data found to analyze trends for the last {days} recorded forecast day(s).")
        return
    
    output_message = (f"📈 **Weather Trends (Analyzed Last {trend_data['analyzed_entry_count']} Forecasts "
                      f"from {trend_data['days_span']} Distinct Day(s) within approx. last {days} recorded days):**\n")
    
    if trend_data.get("coastal") and trend_data["coastal"]:
        most_common_coastal = max(trend_data["coastal"], key=trend_data["coastal"].get)
        output_message += (f"- **Coastal Region Dominant:** {most_common_coastal.capitalize()} "
                           f"(approx. {trend_data['coastal'][most_common_coastal]*100:.1f}% likelihood among analyzed entries)\n")
    else:
        output_message += "- **Coastal Region:** No clear trend based on available data.\n"

    if trend_data.get("forest") and trend_data["forest"]:
        most_common_forest = max(trend_data["forest"], key=trend_data["forest"].get)
        output_message += (f"- **Forest Region Dominant:** {most_common_forest.capitalize()} "
                           f"(approx. {trend_data['forest'][most_common_forest]*100:.1f}% likelihood among analyzed entries)\n")
    else:
        output_message += "- **Forest Region:** No clear trend based on available data.\n"
        
    await ctx.send(output_message)

@bot.command(name="read_weather")
async def read_weather(ctx):
    """Read today's and tomorrow's weather. Requires Weather Reader role or Admin status."""
    # Permission Check using the new helper
    if not await can_read_weather(ctx):
        await ctx.send("❌ You do not have the required role or permissions to read the weather forecast. Contact an admin if you believe this is an error.")
        return
        
    server_id = ctx.guild.id
    now = datetime.now()
    
    # Get today and tomorrow's dates
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Debug logging
    logging.info(f"Reading weather for today ({today}) and tomorrow ({tomorrow})")
    
    # Query for coastal and forest forecasts
    query = '''
        SELECT forecast_date, coastal_forecast_text, forest_forecast_text
        FROM weather_forecast
        WHERE server_id=? AND forecast_date IN (?, ?)
        ORDER BY forecast_date
    '''
    # No DISTINCT needed due to UNIQUE constraint on (server_id, forecast_date)
    result = db_execute(query, (server_id, today, tomorrow), fetchall=True)
    
    logging.info(f"Retrieved {len(result) if result else 0} weather entries for read_weather command by {ctx.author}")

    if result:
        forecast_lines = [
            f"📅 **{format_golarion_date(datetime.strptime(row[0], '%Y-%m-%d'))}**\n" # Date
            f"  🌊 Coastal: {row[1]}\n"  # Coastal forecast
            f"  🌳 Forest: {row[2]}"     # Forest forecast
            for row in result
        ]
        await ctx.send(f"🌦️ **Current Weather Reading**:\n\n" + "\n\n".join(forecast_lines))
    else:
        await ctx.send("⚠️ No current forecast available for today or tomorrow.")

# Admin command to clean up duplicate entries (should be less needed with UNIQUE constraint)
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
            
            # Get Golarion day name for today
            golarion_day = GOLARION_DAYS[now.weekday()]
            
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
                
                # Get today's forecast (coastal and forest) using the explicit date
                forecast_data = db_execute(
                    '''SELECT coastal_forecast_text, forest_forecast_text FROM weather_forecast 
                       WHERE server_id=? AND forecast_date=?''',
                    (guild.id, today_date), fetchone=True
                )
                
                try:
                    if forecast_data:
                        coastal_forecast, forest_forecast = forecast_data
                        
                        # Format the message
                        weather_message = f"\n**Daily Weather Report ({golarion_day})** \n"
                        weather_message += f"• Coastal Region: {coastal_forecast}\n" # Corrected newline
                        weather_message += f"• Fiereni Forest: {forest_forecast}\n" # Corrected newline
                        weather_message += "*May the winds favor your travels!*"
                        
                        await channel.send(weather_message)
                        logging.info(f"Posted weather for {guild.name}")
                    else:
                        await channel.send(f"\n**Daily Weather Report ({golarion_day})** \n⚠️ No forecast available.")
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