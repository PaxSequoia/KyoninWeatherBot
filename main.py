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
            description="**Version 0.0.1c**\nComplete Command Reference",
            color=0x3498db
        )
        
        categories = {
            "📌 Channel Management": ["set_weather_channel", "show_weather_channel"],
            "📅 Forecast Control": ["generate_forecast", "reset_forecast", "view_forecast"],
            "⚡ Active Systems": ["force_weather", "clear_weather"],
            "👥 Role Settings": ["set_weather_reader_role", "view_weather_reader_role"],
            "📊 Analytics": ["view_history", "view_trends"],
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

with sqlite3.connect('weather_bot.db') as conn:
    c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS server_settings
             (server_id INTEGER PRIMARY KEY, weather_channel_id INTEGER, weather_reader_role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS weekly_forecast
             (server_id INTEGER, day TEXT, coastal_weather TEXT, forest_weather TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS historical_weather
             (server_id INTEGER, date TEXT, coastal_weather TEXT, forest_weather TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS active_weather_systems
             (server_id INTEGER, region TEXT, weather_type TEXT, start_date TEXT, duration INTEGER)''')
conn.commit()

# Constants
GOLARION_DAYS = ["Moonday", "Toilday", "Wealday", "Oathday", "Fireday", "Starday", "Sunday"]
SEASONS = {
    "spring": {"temp_range": (50, 70), "weather_types": ["sunny", "rainy", "cloudy", "misty"]},
    "summer": {"temp_range": (75, 95), "weather_types": ["sunny", "stormy", "humid", "foggy"]},
    "autumn": {"temp_range": (45, 65), "weather_types": ["cloudy", "windy", "rainy", "misty"]},
    "winter": {"temp_range": (20, 40), "weather_types": ["snowy", "cold", "cloudy", "foggy"]}
}

@commands.cooldown(rate=1, per=10, type=commands.BucketType.user)

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

def handle_weather_systems(server_id, location):
    c.execute('''SELECT weather_type, duration FROM active_weather_systems 
                 WHERE server_id=? AND region=? AND duration>0''', (server_id, location))
    system = c.fetchone()
    if not system:
        return None
    
    new_duration = system[1] - 1
    if new_duration > 0:
        c.execute('''UPDATE active_weather_systems SET duration=? 
                     WHERE server_id=? AND region=?''', (new_duration, server_id, location))
    else:
        c.execute('''DELETE FROM active_weather_systems 
                     WHERE server_id=? AND region=?''', (server_id, location))
    conn.commit()
    return system[0]

@bot.command(name="set_weather_channel")
@commands.has_permissions(administrator=True)
async def set_weather_channel(ctx, channel: discord.TextChannel):
    """Set the channel for daily weather updates"""
    c.execute('''INSERT OR REPLACE INTO server_settings (server_id, weather_channel_id) 
                 VALUES (?, ?)''', (ctx.guild.id, channel.id))
    conn.commit()
    await ctx.send(f"🌊 Weather updates will be posted in {channel.mention}")

@bot.command(name="show_weather_channel")
@commands.has_permissions(administrator=True)
async def show_weather_channel(ctx):
    """Display the current weather channel"""
    c.execute('''SELECT weather_channel_id FROM server_settings WHERE server_id=?''', (ctx.guild.id,))
    result = c.fetchone()
    if result and (channel := bot.get_channel(result[0])):
        await ctx.send(f"📌 Current weather channel: {channel.mention}")
    else:
        await ctx.send("❌ No weather channel set! Use `!set_weather_channel`")

@bot.command(name="generate_forecast")
@commands.has_permissions(administrator=True)
async def generate_forecast(ctx, use_trends: bool = False):
    """Generate a new weekly weather forecast"""
    season = "winter" if (month := datetime.now().month) in [12,1,2] else \
             "spring" if month in [3,4,5] else \
             "summer" if month in [6,7,8] else "autumn"
    
    c.execute("DELETE FROM weekly_forecast WHERE server_id=?", (ctx.guild.id,))
    for day in GOLARION_DAYS:
        coastal_type, coastal_temp = generate_base_weather(season, "coastal")
        forest_type, forest_temp = generate_base_weather(season, "forest")
        
        if system := handle_weather_systems(ctx.guild.id, "coastal"):
            coastal_type = system
        if system := handle_weather_systems(ctx.guild.id, "forest"):
            forest_type = system

        c.execute('''INSERT INTO weekly_forecast VALUES (?,?,?,?)''',
                  (ctx.guild.id, day, f"{coastal_type.capitalize()}, {coastal_temp}°F", 
                   f"{forest_type.capitalize()}, {forest_temp}°F"))
    conn.commit()
    await ctx.send("✅ New weekly forecast generated!")

@bot.command(name="view_forecast")
async def view_forecast(ctx):
    """View the 7-day forecast in chronological order"""
    forecast = c.execute('''SELECT day, coastal_weather, forest_weather 
                          FROM weekly_forecast WHERE server_id=?''',
                        (ctx.guild.id,)).fetchall()
    
    if not forecast:
        return await ctx.send("ℹ️ No forecast available. Use `!generate_forecast`")
    
    day_order = {day: idx for idx, day in enumerate(GOLARION_DAYS)}
    sorted_forecast = sorted(forecast, key=lambda x: day_order[x[0]])
    
    embed = discord.Embed(
        title="🌦️ 7-Day Forecast (Chronological Order)",
        color=0x87CEEB
    )
    
    for day, coastal, forest in sorted_forecast:
        embed.add_field(
            name=day,
            value=f"**Coastal:** {coastal}\n**Forest:** {forest}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='set_weather_reader_role')
@commands.has_permissions(administrator=True)
async def set_weather_reader_role(ctx, role: discord.Role):
    """Set a role allowed to preview weather forecasts."""
    with sqlite3.connect('weather_bot.db') as conn:
        c = conn.cursor()
        c.execute('''UPDATE server_settings SET weather_reader_role = ? WHERE server_id = ?''',
                  (role.name, ctx.guild.id))
        conn.commit()
    await ctx.send(f"✅ The weather reader role has been set to **{role.name}**.")

@bot.command(name='view_weather_reader_role')
async def view_weather_reader_role(ctx):
    """View the currently set weather reader role."""
    with sqlite3.connect('weather_bot.db') as conn:
        c = conn.cursor()
        c.execute('''SELECT weather_reader_role FROM server_settings WHERE server_id = ?''', (ctx.guild.id,))
        result = c.fetchone()
    if result and result[0]:
        await ctx.send(f"🔎 The weather reader role is currently **{result[0]}**.")
    else:
        await ctx.send("ℹ️ No weather reader role has been set yet.")

@bot.command(name='read_weather')
async def read_weather(ctx):
    """Preview today's and tomorrow's weather if you have the weather reader role."""
    with sqlite3.connect('weather_bot.db') as conn:
        c = conn.cursor()
        
        # Check for reader role setting
        c.execute('''SELECT weather_reader_role FROM server_settings WHERE server_id = ?''', (ctx.guild.id,))
        result = c.fetchone()
        if not result or not result[0]:
            return await ctx.send("❌ No weather reader role has been set. Please ask an admin to set it.")
        
        required_role = result[0]
        
        # Check if the user has the correct role
        if not any(role.name == required_role for role in ctx.author.roles):
            return await ctx.send("🚫 You don't have the required role to preview the weather.")
        
        # Determine today and tomorrow in Golarion days
        today_idx = datetime.now().weekday()
        tomorrow_idx = (today_idx + 1) % 7
        today_name = GOLARION_DAYS[today_idx]
        tomorrow_name = GOLARION_DAYS[tomorrow_idx]
        
        # Fetch forecasts
        forecasts = {}
        for day_name in (today_name, tomorrow_name):
            c.execute('''SELECT coastal_weather, forest_weather FROM weekly_forecast 
                         WHERE server_id = ? AND day = ?''', (ctx.guild.id, day_name))
            row = c.fetchone()
            if row:
                forecasts[day_name] = row
        
    if not forecasts:
        return await ctx.send("ℹ️ No forecast available. Use `!generate_forecast` first.")
    
    embed = discord.Embed(
        title="🌤️ Weather Preview",
        color=0x00BFFF
    )
    
    for day_name, (coastal, forest) in forecasts.items():
        embed.add_field(
            name=day_name,
            value=f"**Coastal Region:** {coastal}\n**Fiereni Forest:** {forest}",
            inline=False
        )
    
    await ctx.send(embed=embed)


@tasks.loop(time=time(0, 0, tzinfo=timezone(get_timezone_offset())))

async def post_daily_weather():
    golarion_day = GOLARION_DAYS[datetime.now().weekday()]
    for server_id, channel_id in c.execute("SELECT server_id, weather_channel_id FROM server_settings"):
        forecast = c.execute('''SELECT coastal_weather, forest_weather FROM weekly_forecast 
                              WHERE server_id=? AND day=?''', (server_id, golarion_day)).fetchone()
        if forecast and (channel := bot.get_channel(channel_id)):
            await channel.send(
                f"🌤️ **Daily Weather Report ({golarion_day})**\n"
                f"• Coastal Region: {forecast[0]}\n"
                f"• Fiereni Forest: {forecast[1]}\n"
                f"*May the winds favor your travels!*"
            )
            c.execute('''INSERT INTO historical_weather VALUES (?,?,?,?)''',
                     (server_id, datetime.now().strftime("%Y-%m-%d"), forecast[0], forecast[1]))
            conn.commit()

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    post_daily_weather.start()
    
bot.run(TOKEN)