from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = (
    "You are Lahore Smog Helper, a friendly assistant that answers questions about "
    "smog, air quality (AQI), masks, air purifiers and health in Lahore, Pakistan. "
    "Keep answers short, practical and easy to understand (max 5 sentences). "
    "Reply in the same language the user writes in (English, Urdu or Roman Urdu). "
    "For serious symptoms like breathing trouble or chest pain, tell them to see a doctor. "
    "If the question is not about smog, air quality or health, politely say you only help with those."
)

# DEBUG = True  ->  asli error screen pe dikhega (masla theek hone ke baad False kar dena)
DEBUG = True


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

            payload = {
                "model": MODEL,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
                "max_tokens": 1500,
                "reasoning_effort": "low",
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

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            msg = "Sorry, kuch masla aa gaya. Dobara try karein."
            if DEBUG:
                msg = "DEBUG - Groq error " + str(e.code) + ": " + detail
            self._send(500, {"reply": msg})
        except Exception as e:
            msg = "Sorry, kuch masla aa gaya. Dobara try karein."
            if DEBUG:
                msg = "DEBUG - " + type(e).__name__ + ": " + str(e)
            self._send(500, {"reply": msg})
