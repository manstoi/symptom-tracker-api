# api/geolocation.py
import requests

def get_location_from_ip():
    """Get approximate location from IP address."""
    try:
        ip_info = requests.get("https://ipinfo.io", timeout=5).json()
        lat, lon = ip_info["loc"].split(",")
        return {"lat": float(lat), "lon": float(lon)}
    except Exception as e:
        return {"error": str(e)}
