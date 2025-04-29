
# Kingdom of Kyonin Weather Bot

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Private%20Use-blue.svg)](LICENSE)
[![Discord Bot](https://img.shields.io/badge/Discord-Weather%20Bot-7289DA.svg)](https://discord.com/)

🌦️ A dynamic, lore-accurate weather system for Pathfinder's Kingdom of Kyonin, built for Discord servers.

## Features

- 📅 7-Day Golarion Calendar Forecasts (Moonday, Toilday, etc.)
- ☀️ Gradual Seasonal Transitions (Temperate Climate)
- ❄️ Rare Cold Snap Events in Winter
- 🌍 Per-Server Channel and Role Settings
- 🛡️ Secure and OWASP Compliant Design
- ⏰ Daily Weather Posting at Midnight (Central US Time)
- 🔄 Weekly Forecast Auto-Generation Every Monday

## Requirements

- Python 3.9+
- `discord.py`
- `python-dotenv`
- SQLite3 (local database)

## Installation

```bash
git clone https://github.com/your-user/kyonin-weather-bot.git
cd kyonin-weather-bot
pip install -r requirements.txt
```

## Setup

Create a `.env` file with your Discord bot token:

```bash
DISCORD_TOKEN=your-bot-token-here
```

## License

© 2025 Kingdom of Kyonin Weather Bot Authors. All rights reserved.

> Bring Golarion's skies to life — one forecast at a time! 🌦️
