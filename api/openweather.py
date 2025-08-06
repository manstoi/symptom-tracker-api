# api/openweather.py
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather_by_latlon(lat, lon):
    """Fetch current weather data, air pollution, and lunar phase from OpenWeather by coordinates."""
    if not API_KEY:
        return {"error": "Missing OpenWeather API key"}


    try:
        # Current weather
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "imperial"
        }
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()

        # Air pollution
        air_url = "https://api.openweathermap.org/data/2.5/air_pollution"
        air_params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY
        }
        a = requests.get(air_url, params=air_params, timeout=5)
        a.raise_for_status()
        air_data = a.json().get("list", [{}])[0]

        # Lunar phase
        lunar_phase = calculate_moon_phase(datetime.now(timezone.utc))

        return {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"],
            "city": data["name"],
            "aqi": air_data.get("main", {}).get("aqi"),
            "pm2_5": air_data.get("components", {}).get("pm2_5"),
            "pm10": air_data.get("components", {}).get("pm10"),
            "lunar_phase": lunar_phase
        }
    
    except requests.RequestException as e:
        return {"error": str(e)}

def calculate_moon_phase(date):
    """Calculate the lunar phase for a given date."""
    # Simple algorithm to determine the moon phase
    new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    days_since_new_moon = (date - new_moon).days
    phase_index = (days_since_new_moon % 29.53) / 29.53

    if phase_index < 0.03 or phase_index > 0.97:
        return "New Moon"
    elif phase_index < 0.25:
        return "Waxing Crescent"
    elif phase_index < 0.27:
        return "First Quarter"
    elif phase_index < 0.48:
        return "Waxing Gibbous"
    elif phase_index < 0.52:
        return "Full Moon"
    elif phase_index < 0.75:
        return "Waning Gibbous"
    elif phase_index < 0.77:
        return "Last Quarter"
    else:
        return "Waning Crescent"