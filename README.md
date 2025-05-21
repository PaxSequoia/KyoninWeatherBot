# Kingdom of Kyonin Weather Bot

A Discord bot for managing and posting immersive weather forecasts for your server, with weekly archiving and historic trend features.

---

## Features

- **Interactive Weather Menu**: Use `!menu` to access weather commands via Discord buttons.
- **Forecast Generation**: Generate a 7-day forecast with `!generate_forecast`. Automatically archives the previous week's forecast.
- **Manual & Scheduled Posting**: Post daily weather updates manually (`!post_weather`) or let the bot post them automatically at midnight (Central Time).
- **Historic Forecast Archive**: 
  - Weekly forecasts are archived automatically when a new week is generated.
  - View archived forecasts with `!historic_forecast [YYYY-MM-DD]`.
  - Admins can manually archive the current week with `!archive_week`.
- **Channel Management**: Set or view the weather channel with `!set_weather_channel #channel` and `!show_weather_channel`.
- **Role Management**: Set or view the weather reader role with `!set_weather_reader_role` and `!view_weather_reader_role`.
- **Forecast Reading**: 
  - `!read_weather` or the "📖 Read Weather" button shows today's and tomorrow's forecast.
  - `!view_forecast [YYYY-MM-DD]` or the "📅 7-Day Forecast" button shows the 7-day forecast.
- **Database Cleanup**: Remove duplicate forecasts with `!cleanup_database`.
- **Help Command**: Use `!weather_help` for a categorized command reference.
- **Ping**: Use `!ping` or the "🏓 Ping" button to check if the bot is responsive.

---

## Commands

| Command                        | Description                                                      |
|--------------------------------|------------------------------------------------------------------|
| `!menu`                        | Show interactive weather system menu.                            |
| `!generate_forecast`           | Generate a new 7-day forecast (archives previous week). (Admin)  |
| `!post_weather`                | Manually post today's weather update. (Admin)                    |
| `!archive_week`                | Manually archive this week's forecast. (Admin)                   |
| `!historic_forecast [date]`    | View archived weekly forecasts.                                  |
| `!set_weather_channel #channel`| Set the channel for weather updates. (Admin)                     |
| `!show_weather_channel`        | Show the current weather channel. (Admin)                        |
| `!set_weather_reader_role @role`| Set the weather reader role. (Admin)                            |
| `!view_weather_reader_role`    | View the weather reader role. (Admin)                            |
| `!read_weather`                | Read today's and tomorrow's weather.                             |
| `!view_forecast [date]`        | View the 7-day forecast from today or a specific date.           |
| `!cleanup_database`            | Remove duplicate forecast entries. (Admin)                       |
| `!ping`                        | Check if the bot is online.                                      |
| `!weather_help`                | Show this help message.                                          |

---

## Historic Forecasts

- **Automatic Archiving**: When a new weekly forecast is generated, the previous week's forecast is archived.
- **Manual Archiving**: Use `!archive_week` to archive the current week at any time.
- **Viewing Archives**: Use `!historic_forecast` to view the most recent archive, or `!historic_forecast YYYY-MM-DD` to view a specific week.

---

## Setup

1. **Clone the repository** and install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

2. **Configure your `.env` file** with your Discord bot token and database credentials:
    ```
    DISCORD_TOKEN=your_token_here
    DATABASE_HOST=localhost
    DATABASE_PORT=3306
    DATABASE_USER=your_user
    DATABASE_PASSWORD=your_password
    DATABASE_NAME=weather_bot
    ```

3. **Run the bot**:
    ```sh
    python src/main.py
    ```

---

## Notes

- The bot uses SQLite for local storage and can be adapted for MySQL.
- Scheduled weather posting runs every 15 minutes and posts at midnight Central Time.
- Only users with admin permissions can use admin commands.

---

## License

MIT License

---
