import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# FIX: Correctly get the API key from an environment variable named 'OPENWEATHER_API_KEY'.
# The previous code mistakenly used the key itself as the variable name.
# You must set this environment variable for the app to work.
API_KEY = os.environ.get("OPENWEATHER_API_KEY")

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def _choose_theme(condition: str) -> str:
    """
    Map OpenWeather 'main' condition to a UI theme token.
    """
    if condition == "Clear":
        return "clear"
    if condition == "Snow":
        return "snow"
    if condition in ("Rain", "Drizzle", "Thunderstorm"):
        return "rain"
    if condition == "Clouds":
        return "clouds"
    return "mist"

def fetch_weather(city: str, units: str = "metric") -> dict:
    """
    Fetch current weather for a city. Returns a dict tailored for templates.
    Raises ValueError with a friendly message if the API returns an error.
    """
    if not API_KEY:
        raise ValueError("Server misconfiguration: OPENWEATHER_API_KEY is not set.")

    params = {"q": city, "appid": API_KEY, "units": units}

    try:
        r = requests.get(BASE_URL, params=params, timeout=10)
    except requests.RequestException as e:
        raise ValueError(f"Network error: {e}")

    try:
        data = r.json()
    except ValueError:
        data = {}

    if r.status_code != 200:
        msg = (data.get("message") or f"HTTP {r.status_code}").capitalize()
        raise ValueError(msg)

    # Defensive parsing
    name = data.get("name") or city
    sys = data.get("sys") or {}
    main = data.get("main") or {}
    wind = data.get("wind") or {}
    weather_list = data.get("weather") or []

    # FIX: The 'weather' key contains a list of dictionaries. Access the first item.
    # The original code would raise an AttributeError if the list was empty.
    w = weather_list[0] if weather_list else {}

    # Build display fields
    condition = w.get("main") or "Clear"
    description = (w.get("description") or condition).title()
    icon_code = w.get("icon") or "01d"
    icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
    theme = _choose_theme(condition)

    temp = main.get("temp")
    feels_like = main.get("feels_like", temp)
    humidity = main.get("humidity")

    # FIX: Made exception handling more specific to avoid masking other errors.
    def _r(v):
        try:
            return int(round(float(v)))
        except (ValueError, TypeError,- TypeError):
            return v

    return {
        "city": name,
        "country": sys.get("country", ""),
        "temp": _r(temp),
        "feels_like": _r(feels_like),
        "humidity": humidity,
        "wind": wind.get("speed"),
        "description": description,
        "condition": condition,
        "icon_url": icon_url,
        "theme": theme,
    }

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/weather", methods=["GET"])
def weather():
    # FIX: Use request.args for GET requests, not request.form.
    # Added a default empty string and strip() to handle input gracefully.
    city = request.args.get('city_name', '').strip()
    units = request.args.get("units", "metric")

    if not city:
        return render_template("home.html", error="Please enter a city.")

    try:
        info = fetch_weather(city, units=units)
    except Exception as e:
        return render_template("home.html", error=str(e))

    return render_template("result.html", info=info, units=units)

# Local dev entrypoint; in Render use Gunicorn via Procfile
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
