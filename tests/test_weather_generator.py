import unittest
import random # For setting seed in tests if needed, and for understanding weather_generator
import sys
import os

# Adjust path to import from the root directory if tests is a top-level folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from weather_generator import (
    weighted_choice,
    get_random_description,
    apply_region_modifiers,
    apply_season_modifiers,
    apply_time_modifiers,
    get_temperature,
    get_weather_components,
    generate_weather_description,
    get_simple_forecast,
    generate_daily_forecast as wg_generate_daily_forecast, # Alias to avoid conflict if any local func
    PRECIPITATION_TYPES,
    CLOUD_COVER,
    WIND_SPEED,
    HUMIDITY_LEVELS,
    SPECIAL_CONDITIONS,
    MAGICAL_EFFECTS,
    REGION_MODIFIERS,
    SEASONS_EXTENDED,
    TIME_OF_DAY
)

class TestWeatherGenerator(unittest.TestCase):

    def test_weighted_choice(self):
        options_single = {"a": {"weight": 100}, "b": {"weight": 0}}
        self.assertEqual(weighted_choice(options_single), "a", "Should select the only weighted option")

        options_dominant = {"a": {"weight": 1}, "b": {"weight": 999999}}
        # Run multiple times to be reasonably sure
        results = [weighted_choice(options_dominant) for _ in range(10)]
        self.assertTrue(all(r == "b" for r in results), "Should heavily favor the dominant option")
        
        options_equal = {"a": {"weight": 1}, "b": {"weight": 1}, "c": {"weight": 1}}
        chosen = weighted_choice(options_equal)
        self.assertIn(chosen, options_equal.keys(), "Chosen option should be a valid key")

        # Test with actual data structure if simple dicts are not representative
        self.assertIn(weighted_choice(PRECIPITATION_TYPES), PRECIPITATION_TYPES.keys())

    def test_get_random_description(self):
        desc = get_random_description(CLOUD_COVER, "clear")
        self.assertIn(desc, CLOUD_COVER["clear"]["description"])

        desc_none = get_random_description(SPECIAL_CONDITIONS, "none")
        self.assertEqual(desc_none, "", "Description for 'none' key should be empty string")
        
        # Test with a key that has multiple descriptions
        desc_multi = get_random_description(WIND_SPEED, "light_breeze")
        self.assertIn(desc_multi, WIND_SPEED["light_breeze"]["description"])

    def _apply_modifier_test_helper(self, apply_func, base_dict, modifier_key_group, category):
        base_weights = {k: v["weight"] for k, v in base_dict.items()}
        
        # Test with actual modifiers
        modified_weights = apply_func(base_weights.copy(), modifier_key_group, category)
        self.assertIsInstance(modified_weights, dict, "Should return a dictionary")
        # Check if at least one weight changed if modifiers exist for the category
        if modifier_key_group in apply_func.__self__.MODIFIERS and category in apply_func.__self__.MODIFIERS[modifier_key_group]: # Accessing MODIFIERS through the function's bound object if it's a method, or directly if global
             if any(key in apply_func.__self__.MODIFIERS[modifier_key_group][category] for key in base_weights):
                  if base_weights != modified_weights : # Ensure they are not identical if modification happened
                    pass # This is a weak check, better to check specific values
        
        # Test with a non-existent modifier key (e.g., invalid region)
        unmodified_weights = apply_func(base_weights.copy(), "non_existent_key", category)
        self.assertEqual(unmodified_weights, base_weights, "Should return base weights if key not found")

        # Test a specific modification if possible
        # Example: if "coastal" doubles "light_rain" weight for "precipitation"
        if modifier_key_group == "coastal" and category == "precipitation" and "light_rain" in base_weights:
            specific_base = {"light_rain": {"weight": 10}}
            specific_weights = {k: v["weight"] for k,v in specific_base.items()}
            # Assuming REGION_MODIFIERS is accessible for direct check of modifier value
            expected_modifier = REGION_MODIFIERS["coastal"]["precipitation"].get("light_rain", 1)
            modified_specific = apply_func(specific_weights, "coastal", "precipitation")
            if "light_rain" in modified_specific: # Check if key still exists
                 self.assertEqual(modified_specific["light_rain"], specific_base["light_rain"]["weight"] * expected_modifier)


    def test_apply_region_modifiers(self):
        # Need to bind REGION_MODIFIERS to the function or pass it, hacky for now
        apply_region_modifiers.__self__ = type("BoundHack", (), {"MODIFIERS": REGION_MODIFIERS})() 
        self._apply_modifier_test_helper(apply_region_modifiers, PRECIPITATION_TYPES, "coastal", "precipitation")
        self._apply_modifier_test_helper(apply_region_modifiers, WIND_SPEED, "forest", "wind_speed")

    def test_apply_season_modifiers(self):
        apply_season_modifiers.__self__ = type("BoundHack", (), {"MODIFIERS": SEASONS_EXTENDED})()
        self._apply_modifier_test_helper(apply_season_modifiers, CLOUD_COVER, "spring", "cloud")
        self._apply_modifier_test_helper(apply_season_modifiers, SPECIAL_CONDITIONS, "winter", "special")

    def test_apply_time_modifiers(self):
        apply_time_modifiers.__self__ = type("BoundHack", (), {"MODIFIERS": TIME_OF_DAY})()
        self._apply_modifier_test_helper(apply_time_modifiers, SPECIAL_CONDITIONS, "dawn", "special")
        self._apply_modifier_test_helper(apply_time_modifiers, MAGICAL_EFFECTS, "night", "magical")

    def test_get_temperature(self):
        seasons = SEASONS_EXTENDED.keys()
        regions = REGION_MODIFIERS.keys()
        times = TIME_OF_DAY.keys()

        for season in seasons:
            for region in regions:
                for time_of_day in times:
                    temp = get_temperature(season, region, time_of_day)
                    self.assertIsInstance(temp, int)
                    
                    base_min, base_max = SEASONS_EXTENDED[season]["temp_range"]
                    region_min_mod, region_max_mod = REGION_MODIFIERS[region].get("temperature_mod", (0,0))
                    time_mod = TIME_OF_DAY[time_of_day].get("temp_mod", 0)
                    
                    expected_min = base_min + region_min_mod + time_mod
                    expected_max = base_max + region_max_mod + time_mod
                    
                    self.assertTrue(expected_min <= temp <= expected_max,
                                    f"Temp {temp} out of range ({expected_min}-{expected_max}) for {season}, {region}, {time_of_day}")

    def test_get_weather_components(self):
        components = get_weather_components("summer", "plains", "midday")
        self.assertIsInstance(components, dict)
        expected_keys = ["precipitation", "cloud_cover", "wind", "wind_speed", 
                         "humidity", "humidity_value", "special", "magical", "temperature"]
        for key in expected_keys:
            self.assertIn(key, components, f"Key '{key}' missing from components")

        self.assertIn(components["precipitation"], PRECIPITATION_TYPES.keys())
        self.assertIn(components["cloud_cover"], CLOUD_COVER.keys())
        self.assertIn(components["wind"], WIND_SPEED.keys())
        self.assertIsInstance(components["wind_speed"], int)
        self.assertTrue(WIND_SPEED[components["wind"]]["speed"][0] <= components["wind_speed"] <= WIND_SPEED[components["wind"]]["speed"][1])
        self.assertIn(components["humidity"], HUMIDITY_LEVELS.keys())
        self.assertIsInstance(components["humidity_value"], int)
        self.assertTrue(0 <= components["humidity_value"] <= 100)
        self.assertIn(components["special"], SPECIAL_CONDITIONS.keys())
        self.assertIn(components["magical"], MAGICAL_EFFECTS.keys())
        self.assertIsInstance(components["temperature"], int)

    def test_generate_weather_description(self):
        # Use a fixed seed for components to make description test more predictable if needed,
        # but description itself has randomness.
        # random.seed(42) 
        components = get_weather_components("autumn", "forest", "evening")
        
        brief = generate_weather_description(components, "autumn", "forest", "evening", style="brief")
        standard = generate_weather_description(components, "autumn", "forest", "evening", style="standard")
        immersive = generate_weather_description(components, "autumn", "forest", "evening", style="immersive")

        self.assertIsInstance(brief, str)
        self.assertTrue(len(brief) > 0)
        
        self.assertIsInstance(standard, str)
        self.assertTrue(len(standard) > 0)
        
        self.assertIsInstance(immersive, str)
        self.assertTrue(len(immersive) > 0)

        # Check relative lengths (general expectation)
        # This can be flaky due to random choices in descriptions.
        # A more robust test would be to check for specific keywords or structure for each style.
        self.assertTrue(len(brief) <= len(standard) or len(standard) <= len(immersive), "Checking general length progression of styles")
        self.assertIn(str(components["temperature"]), brief, "Brief style should contain temperature")

    def test_get_simple_forecast(self):
        forecast_single_brief = get_simple_forecast("spring", "coastal", days=1, style="brief")
        self.assertIsInstance(forecast_single_brief, str)

        forecast_single_standard = get_simple_forecast("summer", "mountains", days=1, style="standard")
        self.assertIsInstance(forecast_single_standard, str)
        self.assertIn(str(get_temperature("summer", "mountains", "morning")), forecast_single_standard, "Standard forecast should reflect temperature range")


        forecast_multi = get_simple_forecast("winter", "plains", days=3, style="standard")
        self.assertIsInstance(forecast_multi, list)
        self.assertEqual(len(forecast_multi), 3)
        for item in forecast_multi:
            self.assertIsInstance(item, str)

    def test_wg_generate_daily_forecast(self): # Test the aliased function
        forecast = wg_generate_daily_forecast(season="spring", region="forest", style="standard")
        self.assertIsInstance(forecast, str)
        self.assertTrue(len(forecast) > 0)
        # Check for temperature presence as a basic content check
        # This requires knowing how temperature is formatted, e.g., "°F"
        self.assertIn("°F", forecast)


if __name__ == '__main__':
    unittest.main()
