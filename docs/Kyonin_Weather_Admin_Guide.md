
# Kingdom of Kyonin Weather Bot

## Server Admin & User Guide (v1.0.3-secure-auto)

---

## 1. Admin Setup

| Command | Purpose |
|:---|:---|
| `!set_weather_channel #channel` | Select where daily weather is posted. |
| `!show_weather_channel` | Show the currently selected weather channel. |
| `!set_weather_reader_role @Role` | Assign a role allowed to preview upcoming weather. |
| `!view_weather_reader_role` | View the current reader role. |
| `!generate_forecast` | (Optional) Manually create a 7-day forecast (auto-generation happens every Monday). |

---

## 2. User Commands

| Command | Purpose |
|:---|:---|
| `!view_forecast` | View the full 7-day weather forecast. |
| `!read_weather` | Preview today's and tomorrow's weather (if you have the reader role). |
| `!ping` | Quick bot responsiveness test. |
| `!help` | See a categorized list of all commands. |

---

## 3. Automatic Behavior

| Action | Details |
|:---|:---|
| **Daily Weather Posting** | Posts today's weather at midnight Central time every day. |
| **Weekly Forecast Generation** | Automatically generates a fresh 7-day forecast every Monday at midnight Central time. |

---

## 4. Lore-Accurate Calendar

- Days of the week match Golarion:
  - `Moonday, Toilday, Wealday, Oathday, Fireday, Starday, Sunday`
- Climate is **temperate**:
  - Milder winters, gradual season changes, rare cold snaps.

---

## 5. Admin Reminders

- Rotate bot tokens periodically for security.
- Watch logs for any database error messages (rare).
- You can regenerate forecasts manually anytime with `!generate_forecast` if needed.

---

## Quick Setup Recap

✅ Invite the bot.  
✅ Set the weather channel.  
✅ (Optionally) Set the reader role.  
✅ Done — bot now runs automatically!

> **Ready to bring Golarion's skies to life in your server!** 🌊🌧️💖
