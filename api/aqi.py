from http.server import BaseHTTPRequestHandler
import json
import urllib.request

# Lahore ka live AQI (Open-Meteo, free, key ki zaroorat nahi)
URL = ("https://air-quality-api.open-meteo.com/v1/air-quality"
       "?latitude=31.5204&longitude=74.3587&current=us_aqi,pm2_5,pm10&timezone=Asia%2FKarachi")


class handler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "public, s-maxage=600, stale-while-revalidate=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            cur = data.get("current") or {}
            aqi = cur.get("us_aqi")
            self._send(200, {
                "aqi": round(aqi) if aqi is not None else None,
                "pm25": round(cur["pm2_5"]) if cur.get("pm2_5") is not None else None,
                "pm10": round(cur["pm10"]) if cur.get("pm10") is not None else None,
                "time": cur.get("time"),
            })
        except Exception as e:
            print("AQI API error:", e)
            self._send(502, {"aqi": None})
