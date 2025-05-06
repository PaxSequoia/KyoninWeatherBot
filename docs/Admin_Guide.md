# Kingdom of Kyonin Weather System
## User Guide - Version 1.0.3-secure

![Weather System Banner](https://i.pinimg.com/736x/3f/45/67/3f4567dd42c96fa41d23ae14d655f3b3.jpg)

## 📋 Table of Contents
- [Introduction](#introduction)
- [Setup Guide](#setup-guide)
- [Command Reference](#command-reference)
- [Interactive Menu](#interactive-menu)
- [Weather Features](#weather-features)
- [Admin Functions](#admin-functions)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## Introduction

The Kingdom of Kyonin Weather System is a Discord bot designed to enhance your roleplaying experience by providing realistic, lore-friendly weather forecasts for your Pathfinder or fantasy-themed Discord server. The bot generates weather patterns following the Golarion calendar system and can be customized to fit the geographical features of your campaign setting.

### Key Features
- 🌦️ Daily weather forecasts with Golarion calendar integration
- 📅 7-day forecasts with temperature and conditions
- ⏱️ Automatic daily weather updates at midnight (US Central Time)
- 🌍 Location-based weather variations (coastal, forest, etc.)
- 📝 Season-appropriate weather patterns
- 👥 Role-based access control for weather reading

## Setup Guide

### Prerequisites
- Administrator permissions on your Discord server
- A designated channel for weather updates

### Initial Setup
1. **Invite the bot** to your Discord server (use the invitation link provided by your bot administrator)
2. **Set a weather channel** where forecasts will be posted:
   ```
   !set_weather_channel #your-weather-channel
   ```
3. **Generate your first forecast** to create weather for the next 7 days:
   ```
   !generate_forecast
   ```

### Verifying Setup
After completing the setup, you can verify everything is working by:
1. Using `!show_weather_channel` to confirm your channel selection
2. Using `!read_weather` to view today's and tomorrow's forecast
3. Using `!view_forecast` to see the 7-day forecast

## Command Reference

### 📌 Channel Management
- `!set_weather_channel #channel` - Sets the channel where daily weather updates will be posted
- `!show_weather_channel` - Shows the currently designated weather channel

### 🗕️ Forecast Control
- `!generate_forecast` - Creates a new 7-day weather forecast
- `!view_forecast` - Shows the current 7-day forecast

### 👥 Role Settings
- `!set_weather_reader_role @role` - Sets which role can use weather reading commands
- `!view_weather_reader_role` - Shows the current weather reader role

### 👁️ Preview
- `!read_weather` - Shows today's and tomorrow's weather forecast

### ⚙️ Utility
- `!ping` - Checks if the bot is online and responsive
- `!menu` - Opens the interactive weather system menu
- `!cleanup_database` - Admin command to remove duplicate forecast entries

## Interactive Menu

The bot includes a convenient interactive menu that can be accessed using the `!menu` command. The menu provides buttons for the most common functions:

- 📖 **Read Weather** - Shows today's and tomorrow's forecast
- 📅 **7-Day Forecast** - Displays the complete 7-day forecast
- 🔮 **Generate Forecast** - Creates a new 7-day forecast (Admin only)
- 📌 **Set Weather Channel** - Instructions for setting the weather channel
- 📺 **Show Weather Channel** - Displays the current weather channel
- 🏓 **Ping** - Checks if the bot is responsive

## Weather Features

### Golarion Calendar System
The bot uses the Pathfinder Golarion calendar for dates:
- **Days of the week**: Moonday, Toilday, Wealday, Oathday, Fireday, Starday, Sunday
- **Months**: Abadius, Calistril, Pharast, Gozran, Desnus, Sarenith, Erastus, Arodus, Rova, Lamashan, Neth, Kuthona

### Weather Types
The weather system incorporates various conditions based on season and location:

- **Spring**: sunny, rainy, cloudy, misty
- **Summer**: sunny, stormy, humid, foggy
- **Autumn**: cloudy, windy, rainy, misty
- **Winter**: snowy, cold, windy, foggy

**Geographic modifiers** affect temperature and weather conditions:
- **Coastal regions**: more stormy and humid conditions, slightly cooler temperatures
- **Forest regions**: more foggy and misty conditions, mild temperature modification

### Daily Updates
The system automatically posts weather updates at midnight (US Central Time) in your designated weather channel.

## Admin Functions

These functions are restricted to server administrators or users with an "Admin" role:

### Managing Forecasts
- Generate new forecasts with `!generate_forecast`
- Clean up database with `!cleanup_database` to remove duplicate entries

### Channel Configuration
- Set and change the weather channel with `!set_weather_channel #channel`
- View current weather channel with `!show_weather_channel`

### Role Management
- Control who can read weather with `!set_weather_reader_role @role`

## Troubleshooting

### Common Issues

1. **Weather updates not appearing**
   - Check that the bot has the correct permissions in your weather channel
   - Verify the weather channel is set correctly with `!show_weather_channel`
   - Generate a new forecast with `!generate_forecast`

2. **Command access denied**
   - Administrative commands require administrator permissions
   - Make sure your role has the required permissions

3. **No forecast data available**
   - Run `!generate_forecast` to create a new 7-day forecast

4. **Duplicated forecast entries**
   - Use `!cleanup_database` to remove duplicates

### Bot Offline
If the bot appears offline or unresponsive:
1. Check if it responds to the `!ping` command
2. Contact your bot administrator if the issue persists

## FAQ

**Q: How often do I need to generate new forecasts?**
A: The bot maintains a 7-day forecast. You only need to generate new forecasts when you run out of forecast days or if you want to change the weather patterns.

**Q: Can I customize the weather patterns?**
A: The current version uses preset patterns based on seasons and terrain. Future updates may include more customization options.

**Q: Does the bot support different time zones?**
A: The bot operates on US Central Time for automatic updates, but you can read the forecast at any time.

**Q: How do I add the bot to my server?**
A: Contact the bot developer for an invitation link specific to your server.

**Q: Can normal users generate forecasts?**
A: No, forecast generation is restricted to administrators to prevent weather manipulation.

---

*This user guide is for Kingdom of Kyonin Weather System v1.0.3-secure. For more information or support, contact your bot administrator.*