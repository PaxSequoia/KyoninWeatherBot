import discord
from discord.ext import commands, tasks
import sqlite3
import random
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta, time, timezone

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Database setup
conn = sqlite3.connect('weather_bot.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS server_settings
             (server_id INTEGER PRIMARY KEY, weather_channel_id INTEGER, weather_reader_role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS weekly_forecast
             (server_id INTEGER, day TEXT, coastal_weather TEXT, forest_weather TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS historical_weather
             (server_id INTEGER, date TEXT, coastal_weather TEXT, forest_weather TEXT)''')
conn.commit()

# Golarion day names
GOLARION_DAYS = ["Moonday", "Toilday", "Wealday", "Oathday", "Fireday", "Starday", "Sunday"]

# Weather generation logic
SEASONS = {
    "spring": {"temp_range": (50, 70), "weather_types": ["sunny", "rainy", "cloudy", "misty"]},
    "summer": {"temp_range": (75, 95), "weather_types": ["sunny", "stormy", "humid", "foggy"]},
    "autumn": {"temp_range": (45, 65), "weather_types": ["cloudy", "windy", "rainy", "misty"]},
    "winter": {"temp_range": (20, 40), "weather_types": ["snowy", "cold", "cloudy", "foggy"]}
}

# Geographical influences
LAKE_ENCARTHAN_INFLUENCE = {
    "humidity_increase": 0.3,  # 30% higher chance of rain or storms near the lake
    "temp_modifier": -5,  # Temperatures are 5°F cooler near the lake in summer, 5°F warmer in winter
}

FOREST_INFLUENCE = {
    "humidity_increase": 0.2,  # 20% higher chance of fog or mist in the forest
    "temp_modifier": -3,  # Temperatures are 3°F cooler in the forest during summer, 3°F warmer in winter
}

def generate_weather(season, location, trend=None):
    """
    Generate a random weather forecast based on the season, location, and optional trend.
    Location can be "coastal" (near Lake Encarthan) or "forest" (old-growth forest).
    Trend is a dictionary of weather types and their probabilities.
    """
    temp_range = SEASONS[season]["temp_range"]
    weather_types = SEASONS[season]["weather_types"]
    
    # Adjust temperature and weather based on location
    if location == "coastal":
        temp_range = (temp_range[0] + LAKE_ENCARTHAN_INFLUENCE["temp_modifier"], temp_range[1] + LAKE_ENCARTHAN_INFLUENCE["temp_modifier"])
        if random.random() < LAKE_ENCARTHAN_INFLUENCE["humidity_increase"]:
            weather_types = ["rainy", "stormy", "humid"] + weather_types
    elif location == "forest":
        temp_range = (temp_range[0] + FOREST_INFLUENCE["temp_modifier"], temp_range[1] + FOREST_INFLUENCE["temp_modifier"])
        if random.random() < FOREST_INFLUENCE["humidity_increase"]:
            weather_types = ["foggy", "misty"] + weather_types
    
    # Adjust probabilities based on trend
    if trend:
        for weather_type, probability in trend.items():
            if weather_type in weather_types:
                weather_types.extend([weather_type] * int(probability * 10))  # Increase likelihood
    
    weather_type = random.choice(weather_types)
    temperature = random.randint(temp_range[0], temp_range[1])
    return f"{weather_type.capitalize()}, {temperature}°F"

def get_current_season():
    """Determine the current season based on the real-world date."""
    today = datetime.now()
    month = today.month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "autumn"

def get_golarion_day():
    """Get the current Golarion day based on the real-world date."""
    today = datetime.now()
    return GOLARION_DAYS[today.weekday()]

def generate_weekly_forecast(server_id, use_trends=False):
    """Generate a weekly forecast and store it in the database."""
    season = get_current_season()
    c.execute("DELETE FROM weekly_forecast WHERE server_id = ?", (server_id,))  # Clear old forecast
    
    # Get trends if enabled
    trend = None
    if use_trends:
        trend = analyze_weather_trends(server_id, return_trend=True)
    
    for day in GOLARION_DAYS:
        coastal_weather = generate_weather(season, "coastal", trend)
        forest_weather = generate_weather(season, "forest", trend)
        c.execute("INSERT INTO weekly_forecast (server_id, day, coastal_weather, forest_weather) VALUES (?, ?, ?, ?)",
                  (server_id, day, coastal_weather, forest_weather))
    conn.commit()

def reset_weekly_forecast(server_id):
    """Reset the weekly forecast for a server."""
    c.execute("DELETE FROM weekly_forecast WHERE server_id = ?", (server_id,))
    conn.commit()

def get_weekly_forecast(server_id):
    """Retrieve the weekly forecast for a server."""
    c.execute("SELECT day, coastal_weather, forest_weather FROM weekly_forecast WHERE server_id = ? ORDER BY day", (server_id,))
    return c.fetchall()

def store_historical_weather(server_id, coastal_weather, forest_weather):
    """Store today's weather in the historical data table."""
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO historical_weather (server_id, date, coastal_weather, forest_weather) VALUES (?, ?, ?, ?)",
              (server_id, today, coastal_weather, forest_weather))
    conn.commit()

def get_historical_weather(server_id, days=7):
    """Retrieve historical weather data for the last `days` days."""
    c.execute("SELECT date, coastal_weather, forest_weather FROM historical_weather WHERE server_id = ? ORDER BY date DESC LIMIT ?",
              (server_id, days))
    return c.fetchall()

def analyze_weather_trends(server_id, days=7, return_trend=False):
    """Analyze weather trends over the last `days` days."""
    historical_data = get_historical_weather(server_id, days)
    if not historical_data:
        return "No historical data available." if not return_trend else None
    
    coastal_trends = {}
    forest_trends = {}
    
    for date, coastal_weather, forest_weather in historical_data:
        coastal_type = coastal_weather.split(",")[0].lower()
        forest_type = forest_weather.split(",")[0].lower()
        
        coastal_trends[coastal_type] = coastal_trends.get(coastal_type, 0) + 1
        forest_trends[forest_type] = forest_trends.get(forest_type, 0) + 1
    
    if return_trend:
        # Return a dictionary of weather types and their probabilities
        total_coastal = sum(coastal_trends.values())
        total_forest = sum(forest_trends.values())
        coastal_trend = {k: v / total_coastal for k, v in coastal_trends.items()}
        forest_trend = {k: v / total_forest for k, v in forest_trends.items()}
        return {"coastal": coastal_trend, "forest": forest_trend}
    else:
        coastal_trend = max(coastal_trends, key=coastal_trends.get)
        forest_trend = max(forest_trends, key=forest_trends.get)
        return f"🌤️ **Weather Trends (Last {days} Days):**\n- **Coastal Region:** {coastal_trend.capitalize()}\n- **Forest Region:** {forest_trend.capitalize()}"

# Task to post daily weather
@tasks.loop(time=time(0, 0, tzinfo=timezone(timedelta(hours=-5))))  # Midnight CST
async def post_daily_weather():
    season = get_current_season()
    golarion_day = get_golarion_day()
    for server_id, channel_id in c.execute("SELECT server_id, weather_channel_id FROM server_settings"):
        forecast = get_weekly_forecast(server_id)
        if forecast:
            for day, coastal_weather, forest_weather in forecast:
                if day == golarion_day:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        await channel.send(
                            f"🌤️ **Today's Weather in Kyonin ({golarion_day}):**\n"
                            f"- **Coastal Region (near Lake Encarthan):** {coastal_weather}\n"
                            f"- **Fiereni Forest:** {forest_weather}"
                        )
                        # Store today's weather in historical data
                        store_historical_weather(server_id, coastal_weather, forest_weather)
                    break

# Command to set the weather channel
@bot.command(name="set_weather_channel")
@commands.has_permissions(administrator=True)
async def set_weather_channel(ctx, channel: discord.TextChannel):
    c.execute("INSERT OR REPLACE INTO server_settings (server_id, weather_channel_id) VALUES (?, ?)",
              (ctx.guild.id, channel.id))
    conn.commit()
    await ctx.send(f"Weather updates will be posted in {channel.mention}.")

# Command to display the currently set weather channel
@bot.command(name="show_weather_channel")
@commands.has_permissions(administrator=True)
async def show_weather_channel(ctx):
    c.execute("SELECT weather_channel_id FROM server_settings WHERE server_id = ?", (ctx.guild.id,))
    result = c.fetchone()
    if result and result[0]:
        channel = bot.get_channel(result[0])
        if channel:
            await ctx.send(f"The current weather channel is {channel.mention}.")
        else:
            await ctx.send("The weather channel is set, but the channel no longer exists.")
    else:
        await ctx.send("No weather channel has been set. Use `!set_weather_channel` to set one.")

# Command to view the current weather reader role
@bot.command(name="view_weather_reader_role")
@commands.has_permissions(administrator=True)
async def view_weather_reader_role(ctx):
    c.execute("SELECT weather_reader_role FROM server_settings WHERE server_id = ?", (ctx.guild.id,))
    result = c.fetchone()
    if result and result[0]:
        await ctx.send(f"The current weather reader role is `{result[0]}`.")
    else:
        await ctx.send("No weather reader role has been set. Use `!set_weather_reader_role` to set one.")

# Command to change the weather reader role
@bot.command(name="set_weather_reader_role")
@commands.has_permissions(administrator=True)
async def set_weather_reader_role(ctx, role: discord.Role):
    c.execute("INSERT OR REPLACE INTO server_settings (server_id, weather_reader_role) VALUES (?, ?)",
              (ctx.guild.id, role.name))
    conn.commit()
    await ctx.send(f"The weather reader role has been set to `{role.name}`.")

# Command to generate a weekly forecast
@bot.command(name="generate_forecast")
@commands.has_permissions(administrator=True)
async def generate_forecast(ctx, use_trends: bool = False):
    generate_weekly_forecast(ctx.guild.id, use_trends=use_trends)
    await ctx.send(f"✅ Weekly forecast generated! {'Trends were used.' if use_trends else ''}")

# Command to reset the weekly forecast
@bot.command(name="reset_forecast")
@commands.has_permissions(administrator=True)
async def reset_forecast(ctx):
    reset_weekly_forecast(ctx.guild.id)
    await ctx.send("✅ Weekly forecast reset!")

# Command to view the entire weekly forecast
@bot.command(name="view_forecast")
@commands.has_permissions(administrator=True)
async def view_forecast(ctx):
    forecast = get_weekly_forecast(ctx.guild.id)
    if not forecast:
        await ctx.send("No forecast found. Use `!generate_forecast` to create one.")
        return
    
    forecast_message = "🌤️ **Weekly Forecast for Kyonin:**\n"
    for day, coastal_weather, forest_weather in forecast:
        forecast_message += (
            f"- **{day}:**\n"
            f"  - **Coastal Region (near Lake Encarthan):** {coastal_weather}\n"
            f"  - **Fiereni Forest:** {forest_weather}\n"
        )
    await ctx.send(forecast_message)

# Command to view historical weather data
@bot.command(name="view_history")
@commands.has_permissions(administrator=True)
async def view_history(ctx, days: int = 7):
    historical_data = get_historical_weather(ctx.guild.id, days)
    if not historical_data:
        await ctx.send("No historical data available.")
        return
    
    history_message = f"🌤️ **Historical Weather (Last {days} Days):**\n"
    for date, coastal_weather, forest_weather in historical_data:
        history_message += (
            f"- **{date}:**\n"
            f"  - **Coastal Region (near Lake Encarthan):** {coastal_weather}\n"
            f"  - **Fiereni Forest:** {forest_weather}\n"
        )
    await ctx.send(history_message)

# Command to analyze weather trends
@bot.command(name="view_trends")
@commands.has_permissions(administrator=True)
async def view_trends(ctx, days: int = 7):
    trends = analyze_weather_trends(ctx.guild.id, days)
    await ctx.send(trends)

# Command to preview weather (for specific roles)
@bot.command(name="read_weather")
@commands.has_role("Weather Reader")  # Replace with your desired role name
async def read_weather(ctx):
    try:
        season = get_current_season()
        today_golarion_day = get_golarion_day()
        tomorrow_golarion_day = GOLARION_DAYS[(datetime.now().weekday() + 1) % 7]  # Next day
        
        # Generate weather for today and tomorrow in both regions
        today_coastal = generate_weather(season, "coastal")
        today_forest = generate_weather(season, "forest")
        tomorrow_coastal = generate_weather(season, "coastal")
        tomorrow_forest = generate_weather(season, "forest")
        
        await ctx.send(
            f"🌤️ **Weather Preview:**\n"
            f"- **Today ({today_golarion_day}):**\n"
            f"  - **Coastal Region (near Lake Encarthan):** {today_coastal}\n"
            f"  - **Fiereni Forest:** {today_forest}\n"
            f"- **Tomorrow ({tomorrow_golarion_day}):**\n"
            f"  - **Coastal Region (near Lake Encarthan):** {tomorrow_coastal}\n"
            f"  - **Fiereni Forest:** {tomorrow_forest}"
        )
    except Exception as e:
        logging.error(f"Error in read_weather command: {e}")
        await ctx.send("An error occurred while generating the weather preview. Please try again later.")

# Simple ping command
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong! 🏓")

# Start the bot
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    post_daily_weather.start()

bot.run(TOKEN)