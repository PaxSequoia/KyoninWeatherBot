import random

def generate_weekly_forecast(proximity):
    """
    Generates a 7-day weather forecast based on proximity settings.
    Proximity contains the influence of mountains, forests, and rivers.
    """
    forecast = []
    for day in range(7):
        # Generate random weather conditions based on proximity values
        temperature = round(random.uniform(15, 30) - proximity["mountains"] * 5, 1)
        precipitation = random.choice(["none", "rain", "heavy rain", "snow"])
        wind_speed = round(random.uniform(5, 20) + proximity["mountains"] * 3, 1)
        cloud_cover = random.choice(["clear", "partly cloudy", "overcast"])
        humidity = round(random.uniform(40, 90) + proximity["forests"] * 10, 1)
        special_event = random.choice(
            [None, "river fog", "heatwave", "thunderstorm", "blizzard"]
            if proximity["river"] > 0.5
            else [None, "heatwave", "thunderstorm", "blizzard"]
        )

        # Add the day's weather to the forecast
        forecast.append({
            "temperature": temperature,
            "precipitation": precipitation,
            "wind_speed": wind_speed,
            "cloud_cover": cloud_cover,
            "humidity": humidity,
            "special_event": special_event,
        })

    return forecast