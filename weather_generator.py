import random
from datetime import datetime, timedelta

# Weather Components
PRECIPITATION_TYPES = {
    "none": {"weight": 50, "description": ["clear", "dry", "cloudless"]},
    "light_rain": {"weight": 20, "description": ["light rain", "drizzle", "scattered showers"]},
    "moderate_rain": {"weight": 15, "description": ["steady rain", "rainfall", "showers"]},
    "heavy_rain": {"weight": 8, "description": ["heavy rain", "downpour", "torrential rain"]},
    "thunderstorm": {"weight": 7, "description": ["thunderstorm", "lightning storm", "thunder and lightning"]},
    "light_snow": {"weight": 5, "description": ["light snow", "flurries", "dusting of snow"]},
    "moderate_snow": {"weight": 3, "description": ["steady snow", "snowfall", "accumulating snow"]},
    "heavy_snow": {"weight": 2, "description": ["heavy snow", "blizzard", "snowstorm"]},
    "sleet": {"weight": 2, "description": ["sleet", "freezing rain", "ice pellets"]},
    "hail": {"weight": 1, "description": ["hail", "hailstorm", "pelting hail"]}
}

CLOUD_COVER = {
    "clear": {"weight": 30, "description": ["clear skies", "cloudless", "pristine sky"]},
    "few_clouds": {"weight": 25, "description": ["few clouds", "mostly clear", "scattered clouds"]},
    "partly_cloudy": {"weight": 20, "description": ["partly cloudy", "broken clouds", "partial cloud cover"]},
    "mostly_cloudy": {"weight": 15, "description": ["mostly cloudy", "considerable cloud cover", "predominantly overcast"]},
    "overcast": {"weight": 10, "description": ["overcast", "gray skies", "complete cloud cover"]}
}

WIND_SPEED = {
    "calm": {"weight": 25, "description": ["calm", "still air", "no breeze"], "speed": (0, 5)},
    "light_breeze": {"weight": 35, "description": ["light breeze", "gentle wind", "mild air current"], "speed": (5, 10)},
    "moderate_wind": {"weight": 25, "description": ["moderate wind", "steady breeze", "noticeable wind"], "speed": (10, 20)},
    "strong_wind": {"weight": 10, "description": ["strong wind", "powerful gusts", "forceful breeze"], "speed": (20, 30)},
    "high_wind": {"weight": 4, "description": ["high wind", "howling gale", "intense wind"], "speed": (30, 40)},
    "gale": {"weight": 1, "description": ["gale", "violent wind", "roaring tempest"], "speed": (40, 60)}
}

HUMIDITY_LEVELS = {
    "arid": {"weight": 10, "description": ["arid", "dry", "parched"], "value": (0, 20)},
    "dry": {"weight": 20, "description": ["dry", "low humidity", "crisp"], "value": (20, 40)},
    "comfortable": {"weight": 35, "description": ["comfortable", "moderate humidity", "pleasant"], "value": (40, 60)},
    "humid": {"weight": 25, "description": ["humid", "moist air", "damp"], "value": (60, 80)},
    "very_humid": {"weight": 10, "description": ["very humid", "heavy moisture", "oppressive humidity"], "value": (80, 100)}
}

VISIBILITY_CONDITIONS = {
    "excellent": {"weight": 30, "description": ["excellent visibility", "clear view", "unlimited sight distance"]},
    "good": {"weight": 30, "description": ["good visibility", "clear conditions", "far-reaching view"]},
    "moderate": {"weight": 20, "description": ["moderate visibility", "somewhat hazy", "limited distance view"]},
    "poor": {"weight": 15, "description": ["poor visibility", "hazy", "restricted sight distance"]},
    "very_poor": {"weight": 5, "description": ["very poor visibility", "dense fog", "severely limited visibility"]}
}

SPECIAL_CONDITIONS = {
    "none": {"weight": 70, "description": [""]},
    "fog": {"weight": 10, "description": ["foggy patches", "mist rising", "morning fog"]},
    "heavy_fog": {"weight": 5, "description": ["heavy fog", "thick mist", "enveloping fog"]},
    "frost": {"weight": 5, "description": ["frost", "rime", "frozen dew"]},
    "dust": {"weight": 3, "description": ["dust in the air", "dusty conditions", "airborne particles"]},
    "smoke": {"weight": 2, "description": ["smoke haze", "distant fire smoke", "smoky air"]},
    "rainbow": {"weight": 3, "description": ["rainbow visible", "colorful arc", "prismatic display"]},
    "aurora": {"weight": 2, "description": ["auroral display", "dancing lights", "celestial glow"]}
}

MAGICAL_EFFECTS = {
    "none": {"weight": 85, "description": [""]},
    "minor_arcane": {"weight": 5, "description": ["faint arcane shimmer", "subtle magical resonance", "whisper of magic"]},
    "elemental": {"weight": 4, "description": ["elemental traces", "primal energy currents", "natural magic influence"]},
    "fey_influence": {"weight": 3, "description": ["fey presence", "fairy light", "enchanted atmosphere"]},
    "planar_leak": {"weight": 2, "description": ["planar energies", "otherworldly influence", "dimensional thin spot"]},
    "wild_magic": {"weight": 1, "description": ["wild magic fluctuations", "chaotic magical ripples", "unpredictable arcane currents"]}
}

# Region-specific modifiers
REGION_MODIFIERS = {
    "coastal": {
        "precipitation": {"light_rain": 1.2, "moderate_rain": 1.1, "thunderstorm": 0.8},
        "wind_speed": {"moderate_wind": 1.3, "strong_wind": 1.5, "high_wind": 1.2},
        "special": {"fog": 1.5, "heavy_fog": 1.2},
        "temperature_mod": (-3, 0),  # Cooler due to sea breeze
        "humidity_mod": 20,  # Higher humidity near coast
        "description_prefix": ["coastal", "seaside", "maritime"]
    },
    "forest": {
        "precipitation": {"light_rain": 1.1, "moderate_rain": 1.1},
        "wind_speed": {"calm": 1.3, "light_breeze": 1.2},
        "special": {"fog": 1.3, "heavy_fog": 1.1},
        "magical": {"fey_influence": 2.0},
        "temperature_mod": (-2, -1),  # Slightly cooler in the shade
        "humidity_mod": 10,  # Slightly more humid due to vegetation
        "description_prefix": ["forest", "woodland", "sylvan"]
    },
    "mountains": {
        "precipitation": {"light_snow": 1.5, "moderate_snow": 1.3, "heavy_snow": 1.2},
        "wind_speed": {"strong_wind": 1.5, "high_wind": 1.3, "gale": 1.2},
        "special": {"frost": 1.5},
        "temperature_mod": (-10, -5),  # Much cooler at elevation
        "humidity_mod": -10,  # Drier at higher elevations
        "description_prefix": ["mountain", "alpine", "highland"]
    },
    "plains": {
        "precipitation": {"none": 1.2},
        "wind_speed": {"moderate_wind": 1.2, "strong_wind": 1.1},
        "special": {"dust": 1.3},
        "temperature_mod": (0, 3),  # Warmer due to sun exposure
        "humidity_mod": -5,  # Slightly drier
        "description_prefix": ["plains", "grassland", "open"]
    },
    "desert": {
        "precipitation": {"none": 2.0},
        "wind_speed": {"calm": 1.2, "light_breeze": 1.1, "strong_wind": 1.1},
        "special": {"dust": 1.5},
        "temperature_mod": (5, 15),  # Much warmer
        "humidity_mod": -30,  # Very dry
        "description_prefix": ["desert", "arid", "sandy"]
    },
    "swamp": {
        "precipitation": {"light_rain": 1.3, "moderate_rain": 1.2},
        "wind_speed": {"calm": 1.5},
        "special": {"fog": 1.5, "heavy_fog": 1.3},
        "magical": {"minor_arcane": 1.2, "fey_influence": 1.2},
        "temperature_mod": (0, 2),  # Slightly warmer due to humidity
        "humidity_mod": 30,  # Very humid
        "description_prefix": ["swamp", "marsh", "boggy"]
    }
}

# Season configuration with more detailed attributes
SEASONS_EXTENDED = {
    "spring": {
        "temp_range": (50, 70),
        "precipitation_mod": {"light_rain": 1.5, "moderate_rain": 1.3, "thunderstorm": 1.2},
        "cloud_mod": {"few_clouds": 1.2, "partly_cloudy": 1.3},
        "wind_mod": {"light_breeze": 1.3, "moderate_wind": 1.2},
        "special_mod": {"fog": 1.3, "rainbow": 1.5},
        "magical_mod": {"fey_influence": 1.5},
        "description_prefix": ["spring", "vernal", "budding"],
        "flora_descriptions": [
            "blossoming trees", "sprouting wildflowers", "fresh greenery",
            "budding foliage", "emerging shoots", "vibrant new growth"
        ]
    },
    "summer": {
        "temp_range": (75, 95),
        "precipitation_mod": {"thunderstorm": 1.5, "heavy_rain": 1.3},
        "cloud_mod": {"clear": 1.5, "few_clouds": 1.3},
        "wind_mod": {"calm": 1.2, "light_breeze": 1.3},
        "special_mod": {"dust": 1.3},
        "magical_mod": {"elemental": 1.3},
        "description_prefix": ["summer", "estival", "sun-soaked"],
        "flora_descriptions": [
            "lush foliage", "full bloom flowers", "verdant growth",
            "thick vegetation", "dense canopy", "vibrant greenery"
        ]
    },
    "autumn": {
        "temp_range": (45, 65),
        "precipitation_mod": {"light_rain": 1.2, "moderate_rain": 1.3},
        "cloud_mod": {"partly_cloudy": 1.3, "mostly_cloudy": 1.2},
        "wind_mod": {"moderate_wind": 1.4, "strong_wind": 1.2},
        "special_mod": {"fog": 1.2},
        "magical_mod": {"wild_magic": 1.3},
        "description_prefix": ["autumn", "fall", "harvest"],
        "flora_descriptions": [
            "golden foliage", "falling leaves", "changing colors",
            "russet tones", "amber canopy", "crimson and gold landscape"
        ]
    },
    "winter": {
        "temp_range": (30, 50),
        "precipitation_mod": {"light_snow": 1.5, "moderate_snow": 1.3, "heavy_snow": 1.2},
        "cloud_mod": {"overcast": 1.5, "mostly_cloudy": 1.3},
        "wind_mod": {"strong_wind": 1.3, "high_wind": 1.2},
        "special_mod": {"frost": 1.5},
        "magical_mod": {"planar_leak": 1.2},
        "description_prefix": ["winter", "hibernal", "frost-touched"],
        "flora_descriptions": [
            "bare branches", "snow-covered vegetation", "dormant plants",
            "ice-laden trees", "evergreen contrast", "frozen landscape"
        ]
    }
}

# Time of day modifiers
TIME_OF_DAY = {
    "dawn": {
        "temp_mod": -5,
        "special_mod": {"fog": 1.5, "heavy_fog": 1.3},
        "description_prefix": ["dawn", "early morning", "sunrise"],
        "color_descriptors": ["golden", "amber", "rosy", "pink-tinged"]
    },
    "morning": {
        "temp_mod": 0,
        "special_mod": {"fog": 1.2},
        "description_prefix": ["morning", "forenoon", "ante meridiem"],
        "color_descriptors": ["bright", "clear", "fresh"]
    },
    "midday": {
        "temp_mod": 5,
        "special_mod": {"dust": 1.2},
        "description_prefix": ["midday", "noon", "zenith"],
        "color_descriptors": ["brilliant", "harsh", "white", "intense"]
    },
    "afternoon": {
        "temp_mod": 3,
        "special_mod": {"dust": 1.1},
        "description_prefix": ["afternoon", "post meridiem", "declining day"],
        "color_descriptors": ["warm", "golden", "mellowing"]
    },
    "evening": {
        "temp_mod": -2,
        "special_mod": {"fog": 1.1},
        "description_prefix": ["evening", "dusk", "twilight"],
        "color_descriptors": ["fading", "dusky", "deepening"]
    },
    "night": {
        "temp_mod": -8,
        "special_mod": {"aurora": 1.5},
        "magical_mod": {"fey_influence": 1.2, "planar_leak": 1.2},
        "description_prefix": ["night", "nocturnal", "after dark"],
        "color_descriptors": ["silvery", "shadowy", "moonlit", "star-speckled"]
    }
}

# Helper functions
def weighted_choice(options_dict):
    """Select a random item based on weight."""
    choices = []
    weights = []
    
    for item, attrs in options_dict.items():
        choices.append(item)
        weights.append(attrs["weight"])
        
    return random.choices(choices, weights=weights, k=1)[0]

def get_random_description(options_dict, selected_key):
    """Get a random description for the selected key."""
    if selected_key == "none":
        return ""
    descriptions = options_dict[selected_key]["description"]
    return random.choice(descriptions)

def apply_region_modifiers(base_weights, region, category):
    """Apply regional modifiers to weights."""
    if region not in REGION_MODIFIERS:
        return base_weights
        
    modified_weights = base_weights.copy()
    
    if category in REGION_MODIFIERS[region]:
        modifiers = REGION_MODIFIERS[region][category]
        for key, mod in modifiers.items():
            if key in modified_weights:
                modified_weights[key] *= mod
    
    return modified_weights

def apply_season_modifiers(base_weights, season, category):
    """Apply seasonal modifiers to weights."""
    if season not in SEASONS_EXTENDED:
        return base_weights
        
    modified_weights = base_weights.copy()
    
    mod_key = f"{category}_mod"
    if mod_key in SEASONS_EXTENDED[season]:
        modifiers = SEASONS_EXTENDED[season][mod_key]
        for key, mod in modifiers.items():
            if key in modified_weights:
                modified_weights[key] *= mod
    
    return modified_weights

def apply_time_modifiers(base_weights, time_of_day, category):
    """Apply time of day modifiers to weights."""
    if time_of_day not in TIME_OF_DAY:
        return base_weights
        
    modified_weights = base_weights.copy()
    
    mod_key = f"{category}_mod"
    if mod_key in TIME_OF_DAY[time_of_day]:
        modifiers = TIME_OF_DAY[time_of_day][mod_key]
        for key, mod in modifiers.items():
            if key in modified_weights:
                modified_weights[key] *= mod
    
    return modified_weights

def get_temperature(season, region, time_of_day):
    """Generate a temperature based on season, region, and time of day."""
    # Base temperature from season
    base_min, base_max = SEASONS_EXTENDED[season]["temp_range"]
    
    # Apply region modifier
    region_min_mod, region_max_mod = REGION_MODIFIERS[region]["temperature_mod"]
    adjusted_min = base_min + region_min_mod
    adjusted_max = base_max + region_max_mod
    
    # Apply time of day modifier
    time_mod = TIME_OF_DAY[time_of_day].get("temp_mod", 0)
    adjusted_min += time_mod
    adjusted_max += time_mod
    
    # Random temperature within range
    return random.randint(adjusted_min, adjusted_max)

def get_weather_components(season, region, time_of_day, prev_conditions=None):
    """Generate all weather components based on parameters."""
    
    # Apply continuity if we have previous conditions
    if prev_conditions:
        # Implement weather pattern continuity logic here
        pass
    
    # Get precipitation
    precip_weights = {k: v["weight"] for k, v in PRECIPITATION_TYPES.items()}
    precip_weights = apply_region_modifiers(precip_weights, region, "precipitation")
    precip_weights = apply_season_modifiers(precip_weights, season, "precipitation")
    precipitation = weighted_choice(PRECIPITATION_TYPES)
    
    # Get cloud cover
    cloud_weights = {k: v["weight"] for k, v in CLOUD_COVER.items()}
    cloud_weights = apply_region_modifiers(cloud_weights, region, "cloud")
    cloud_weights = apply_season_modifiers(cloud_weights, season, "cloud")
    cloud_cover = weighted_choice(CLOUD_COVER)
    
    # If we have precipitation, adjust cloud cover accordingly
    if precipitation != "none":
        cloud_cover = random.choice(["mostly_cloudy", "overcast"])
    
    # Get wind speed
    wind_weights = {k: v["weight"] for k, v in WIND_SPEED.items()}
    wind_weights = apply_region_modifiers(wind_weights, region, "wind_speed")
    wind_weights = apply_season_modifiers(wind_weights, season, "wind")
    wind = weighted_choice(WIND_SPEED)
    wind_speed = random.randint(WIND_SPEED[wind]["speed"][0], WIND_SPEED[wind]["speed"][1])
    
    # Get humidity
    base_humidity = random.choice(list(HUMIDITY_LEVELS.keys()))
    humidity_value = random.randint(
        HUMIDITY_LEVELS[base_humidity]["value"][0], 
        HUMIDITY_LEVELS[base_humidity]["value"][1]
    )
    
    # Apply region humidity modifier
    humidity_mod = REGION_MODIFIERS[region].get("humidity_mod", 0)
    humidity_value = max(0, min(100, humidity_value + humidity_mod))
    
    # Recalculate humidity level based on the adjusted value
    for level, data in HUMIDITY_LEVELS.items():
        if data["value"][0] <= humidity_value <= data["value"][1]:
            humidity = level
            break
    else:
        humidity = "comfortable"  # fallback
    
    # Get special conditions
    special_weights = {k: v["weight"] for k, v in SPECIAL_CONDITIONS.items()}
    special_weights = apply_region_modifiers(special_weights, region, "special")
    special_weights = apply_season_modifiers(special_weights, season, "special")
    special_weights = apply_time_modifiers(special_weights, time_of_day, "special")
    special = weighted_choice(SPECIAL_CONDITIONS)
    
    # Get magical effects
    magical_weights = {k: v["weight"] for k, v in MAGICAL_EFFECTS.items()}
    magical_weights = apply_region_modifiers(magical_weights, region, "magical")
    magical_weights = apply_season_modifiers(magical_weights, season, "magical")
    magical_weights = apply_time_modifiers(magical_weights, time_of_day, "magical")
    magical = weighted_choice(MAGICAL_EFFECTS)
    
    # Get temperature
    temperature = get_temperature(season, region, time_of_day)
    
    # Return all weather components
    return {
        "precipitation": precipitation,
        "cloud_cover": cloud_cover,
        "wind": wind,
        "wind_speed": wind_speed,
        "humidity": humidity,
        "humidity_value": humidity_value,
        "special": special,
        "magical": magical,
        "temperature": temperature
    }

def generate_weather_description(components, season, region, time_of_day, style="standard"):
    """Generate a descriptive weather text from components."""
    
    # Extract components
    precipitation = components["precipitation"]
    cloud_cover = components["cloud_cover"]
    wind = components["wind"]
    wind_speed = components["wind_speed"]
    special = components["special"]
    magical = components["magical"]
    temperature = components["temperature"]
    
    # Get descriptions
    precip_desc = get_random_description(PRECIPITATION_TYPES, precipitation)
    cloud_desc = get_random_description(CLOUD_COVER, cloud_cover)
    wind_desc = get_random_description(WIND_SPEED, wind)
    special_desc = get_random_description(SPECIAL_CONDITIONS, special)
    magical_desc = get_random_description(MAGICAL_EFFECTS, magical)
    
    # Region prefix
    region_prefix = random.choice(REGION_MODIFIERS[region]["description_prefix"])
    
    # Season prefix
    season_prefix = random.choice(SEASONS_EXTENDED[season]["description_prefix"])
    
    # Time prefix
    time_prefix = random.choice(TIME_OF_DAY[time_of_day]["description_prefix"])
    
    # Flora description for the season
    flora_desc = random.choice(SEASONS_EXTENDED[season]["flora_descriptions"])
    
    # Color descriptor for time of day
    color_desc = random.choice(TIME_OF_DAY[time_of_day]["color_descriptors"])
    
    # Construct description based on style
    if style == "brief":
        # Brief style: just temperature and main conditions
        main_condition = precip_desc if precipitation != "none" else cloud_desc
        return f"{main_condition} and {temperature}°F"
        
    elif style == "standard":
        # Standard style: main weather components
        parts = []
        
        # Temperature description
        if temperature < 32:
            temp_desc = "freezing"
        elif temperature < 50:
            temp_desc = "cold"
        elif temperature < 65:
            temp_desc = "cool"
        elif temperature < 75:
            temp_desc = "mild"
        elif temperature < 85:
            temp_desc = "warm"
        elif temperature < 95:
            temp_desc = "hot"
        else:
            temp_desc = "scorching"
        
        # Main weather condition
        if precipitation != "none":
            parts.append(f"{precip_desc}")
        else:
            parts.append(f"{cloud_desc}")
        
        # Add wind if significant
        if wind != "calm":
            parts.append(f"with {wind_desc}")
        
        # Add special condition if present
        if special != "none":
            parts.append(f"and {special_desc}")
        
        # Add temperature
        description = f"{', '.join(parts)}. {temp_desc} at {temperature}°F"
        return description
        
    elif style == "immersive":
        # Immersive style: rich, detailed description
        description = f"The {time_prefix} sky over the {region_prefix} lands is {color_desc}"
        
        # Cloud and precipitation
        if precipitation != "none":
            description += f", with {precip_desc} falling from {cloud_desc}"
        else:
            description += f" with {cloud_desc}"
        
        # Wind description
        if wind != "calm":
            description += f". {wind_desc.capitalize()} stirs the {flora_desc}"
        else:
            description += f". The air is {wind_desc}, barely disturbing the {flora_desc}"
        
        # Special effects
        if special != "none":
            description += f". {special_desc.capitalize()} adds to the {season_prefix} atmosphere"
        
        # Magical effects
        if magical != "none":
            description += f", while {magical_desc} can be sensed by the magically attuned"
        
        # Temperature
        description += f". The temperature stands at {temperature}°F"
        
        return description
    
    else:
        # Default fallback
        return f"{cloud_desc} with {precip_desc}, {wind_desc}. Currently {temperature}°F"

def get_weather_forecast(server_id, dates=None, season=None, region=None, style="standard"):
    """Generate a weather forecast for specified dates."""
    if not dates:
        # Default to 7 days starting today
        today = datetime.now()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    if not season:
        # Determine season based on current month
        month = datetime.now().month
        if 3 <= month <= 5:
            season = "spring"
        elif 6 <= month <= 8:
            season = "summer"
        elif 9 <= month <= 11:
            season = "autumn"
        else:
            season = "winter"
    
    if not region:
        region = "coastal"  # Default region
    
    # Generate weather patterns with some continuity
    forecasts = {}
    prev_components = None
    
    for date_str in dates:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Generate for multiple times of day
        day_forecasts = {}
        for time_of_day in ["morning", "afternoon", "night"]:
            components = get_weather_components(season, region, time_of_day, prev_components)
            description = generate_weather_description(components, season, region, time_of_day, style)
            day_forecasts[time_of_day] = {
                "description": description,
                "components": components
            }
            
            # Update previous components for continuity
            if time_of_day == "afternoon":  # Use afternoon weather as the reference
                prev_components = components
        
        forecasts[date_str] = day_forecasts
    
    return forecasts

def get_simple_forecast(season, region, days=1, style="brief"):
    """Generate a simplified forecast for the specified parameters."""
    forecasts = []
    
    for _ in range(days):
        # Pick a random time of day for simplicity
        time_of_day = random.choice(["morning", "afternoon", "evening"])
        
        # Generate components
        components = get_weather_components(season, region, time_of_day)
        
        # Generate description
        description = generate_weather_description(components, season, region, time_of_day, style)
        
        forecasts.append(description)
    
    return forecasts[0] if days == 1 else forecasts

# Function to be called from the main bot code
def generate_daily_forecast(season="spring", region="coastal", style="brief"):
    """Generate a single day's forecast - this replaces the original function."""
    return get_simple_forecast(season, region, days=1, style=style)
