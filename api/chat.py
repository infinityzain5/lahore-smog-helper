from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are Lahore Smog Helper, a friendly assistant that answers questions about "
    "smog, air quality (AQI), masks, air purifiers and health in Lahore, Pakistan. "
    "Keep answers short, practical and easy to understand (max 5 sentences). "
    "Reply in the same language the user writes in (English, Urdu or Roman Urdu). "
    "For serious symptoms like breathing trouble or chest pain, tell them to see a doctor. "
    "If the question is not about smog, air quality or health, politely say you only help with those."
)


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

            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                self._send(500, {"reply": "Server setup problem: API key missing."})
                return

            payload = {
                "model": MODEL,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
                "max_tokens": 400,
                "temperature": 0.6,
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
        except Exception as e:
            self._send(500, {"reply": "Sorry, kuch masla aa gaya. Dobara try karein."})
