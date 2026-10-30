from http.server import BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
import urllib.request
import urllib.error

MODEL = "openai/gpt-oss-20b"

# Lahore ke coordinates (live aur forecast data yahin ka aayega)
LAT, LON = 31.5204, 74.3587
TZ = "Asia%2FKarachi"
AIR_URL = ("https://air-quality-api.open-meteo.com/v1/air-quality"
           "?latitude=%s&longitude=%s&current=us_aqi,pm2_5,pm10&hourly=us_aqi"
           "&forecast_days=7&timezone=%s" % (LAT, LON, TZ))
WX_URL = ("https://api.open-meteo.com/v1/forecast"
          "?latitude=%s&longitude=%s"
          "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code"
          "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
          "precipitation_probability_max,wind_speed_10m_max"
          "&forecast_days=7&timezone=%s" % (LAT, LON, TZ))

SYSTEM_PROMPT = (
    "You are Lahore Smog Helper, a friendly assistant that answers questions about "
    "smog, air quality (AQI), weather, rain, masks, air purifiers and health in Lahore, Pakistan. "
    "Keep answers short, practical and easy to understand. "
    "Reply in the same language the user writes in. If they write Roman Urdu (Urdu in English letters), "
    "reply fully in Roman Urdu, not English. "
    "For serious symptoms like breathing trouble or chest pain, tell them to see a doctor. "
    "If the question is not about smog, air quality, weather or health, politely say you only help with those. "
    "For questions about the current AQI or weather, answer ONLY from the LIVE DATA below and mention the numbers. "
    "For questions about tomorrow, the coming days or next week (weather, rain, temperature, AQI), use the FORECAST list below. "
    "For a week forecast, give a compact summary: one short line per day starting with '- ', then one short tip. "
    "These are model forecasts, so use words like 'expected' or 'likely', and say AQI forecasts are less certain. "
    "If a day has no AQI forecast, say it is not available for that day. "
    "Never invent numbers and never mention anything that is not in the LIVE DATA. "
    "If a message starts with [My current AQI is ...], that is the user's own reading, use it for advice. "
)

DEBUG = False


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode("utf-8"))


def aqi_label(v):
    if v <= 50: return "Good"
    if v <= 100: return "Moderate"
    if v <= 150: return "Unhealthy for Sensitive Groups"
    if v <= 200: return "Unhealthy"
    if v <= 300: return "Very Unhealthy"
    return "Hazardous"


def weather_label(code):
    if code == 0: return "clear sky"
    if code in (1, 2, 3): return "partly cloudy / cloudy"
    if code in (45, 48): return "fog"
    if 51 <= code <= 67: return "drizzle / rain"
    if 71 <= code <= 77: return "snow"
    if 80 <= code <= 82: return "rain showers"
    if code >= 95: return "thunderstorm"
    return "unclear"


def _at(d, key, i):
    try:
        return d.get(key, [])[i]
    except Exception:
        return None


def build_text(air_json, wx_json):
    air = (air_json or {}).get("current") or {}
    wx = (wx_json or {}).get("current") or {}
    cur = []
    if air.get("us_aqi") is not None:
        v = round(air["us_aqi"])
        cur.append("US AQI: %s (%s)" % (v, aqi_label(v)))
        if air.get("pm2_5") is not None:
            cur.append("PM2.5: %s ug/m3" % round(air["pm2_5"]))
        if air.get("pm10") is not None:
            cur.append("PM10: %s ug/m3" % round(air["pm10"]))
    if wx.get("temperature_2m") is not None:
        feels = wx.get("apparent_temperature", wx["temperature_2m"])
        cur.append("Temperature: %s C (feels like %s C)" % (round(wx["temperature_2m"]), round(feels)))
    if wx.get("relative_humidity_2m") is not None:
        cur.append("Humidity: %s%%" % wx["relative_humidity_2m"])
    if wx.get("wind_speed_10m") is not None:
        cur.append("Wind: %s km/h" % round(wx["wind_speed_10m"]))
    if wx.get("weather_code") is not None:
        cur.append("Sky: " + weather_label(wx["weather_code"]))

    # hourly AQI -> daily average / peak
    aqi_days = {}
    h = (air_json or {}).get("hourly") or {}
    for t, v in zip(h.get("time", []), h.get("us_aqi", [])):
        if v is not None:
            aqi_days.setdefault(t[:10], []).append(v)

    fc = []
    d = (wx_json or {}).get("daily") or {}
    for i, date in enumerate(d.get("time", [])):
        try:
            name = datetime.strptime(date, "%Y-%m-%d").strftime("%a %d %b")
        except Exception:
            name = date
        parts = [name]
        tmin, tmax = _at(d, "temperature_2m_min", i), _at(d, "temperature_2m_max", i)
        if tmin is not None and tmax is not None:
            parts.append("%s-%s C" % (round(tmin), round(tmax)))
        code = _at(d, "weather_code", i)
        if code is not None:
            parts.append(weather_label(code))
        prob, mm = _at(d, "precipitation_probability_max", i), _at(d, "precipitation_sum", i)
        if prob is not None:
            parts.append("rain chance %s%%" % prob)
        if mm is not None:
            parts.append("rain %s mm" % mm)
        vals = aqi_days.get(date)
        if vals:
            avg, peak = round(sum(vals) / len(vals)), round(max(vals))
            parts.append("AQI avg %s (%s), peak %s" % (avg, aqi_label(avg), peak))
        else:
            parts.append("AQI forecast not available")
        fc.append("- " + ", ".join(parts))

    if not cur and not fc:
        return ("LIVE DATA: not available right now. If the user asks for AQI, weather or a forecast, "
                "say you cannot fetch live data at the moment and suggest checking IQAir, AQI.in or a weather app.")
    text = "LIVE DATA for Lahore (fetched just now, source: Open-Meteo, modelled data, may differ slightly from ground monitors). "
    if cur:
        text += "CURRENT: " + "; ".join(cur) + ". "
    if fc:
        text += "FORECAST (next days):\n" + "\n".join(fc)
    return text


def live_data_text():
    air_json = wx_json = None
    with ThreadPoolExecutor(max_workers=2) as ex:
        fa = ex.submit(_get, AIR_URL)
        fw = ex.submit(_get, WX_URL)
        try:
            air_json = fa.result(timeout=8)
        except Exception as e:
            print("AIR API error:", e)
        try:
            wx_json = fw.result(timeout=8)
        except Exception as e:
            print("WEATHER API error:", e)
    return build_text(air_json, wx_json)


class handler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            history = body.get("messages", [])[-10:]

            api_key = (os.environ.get("GROQ_API_KEY") or "").strip()
            if not api_key:
                self._send(500, {"reply": "Server setup problem: GROQ_API_KEY missing hai."})
                return

            system = SYSTEM_PROMPT + "\n\n" + live_data_text()
            payload = {
                "model": MODEL,
                "messages": [{"role": "system", "content": system}] + history,
                "max_tokens": 1800,
                "reasoning_effort": "low",
                "temperature": 0.5,
            }
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + api_key,
                    "User-Agent": "Mozilla/5.0",
                },
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            reply = result["choices"][0]["message"]["content"]
            self._send(200, {"reply": reply})

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            print("GROQ HTTP error:", e.code, detail)
            msg = "Sorry, kuch masla aa gaya. Dobara try karein."
            if DEBUG:
                msg = "DEBUG - Groq error " + str(e.code) + ": " + detail
            self._send(500, {"reply": msg})
        except Exception as e:
            print("ERROR:", type(e).__name__, e)
            msg = "Sorry, kuch masla aa gaya. Dobara try karein."
            if DEBUG:
                msg = "DEBUG - " + type(e).__name__ + ": " + str(e)
            self._send(500, {"reply": msg})
