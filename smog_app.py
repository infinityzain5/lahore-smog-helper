import streamlit as st
import requests
from groq import Groq

st.set_page_config(page_title="Lahore Smog Helper", page_icon="🌫️", layout="centered")

# ---------- STYLING (premium look) ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, .stApp { font-family: 'Poppins', sans-serif; }

.stApp {
    background:
        radial-gradient(900px 500px at 0% 0%, rgba(34, 255, 106, 0.22) 0%, transparent 60%),
        radial-gradient(700px 400px at 100% 100%, rgba(34, 255, 106, 0.12) 0%, transparent 60%),
        #050806;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

.block-container { padding-top: 2rem; max-width: 760px; }

.hero { text-align: center; padding: 1.2rem 0 0.6rem 0; }
.hero h1 {
    font-size: 2.2rem; font-weight: 700; margin: 0;
    background: linear-gradient(90deg, #b6ffd0, #22ff6a);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p { color: #8fb3a0; margin-top: .4rem; font-size: .95rem; }

.orb {
    width: 64px; height: 64px; margin: 0 auto 12px auto; border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #b6ffd0, #22ff6a 55%, #0a6b2c);
    box-shadow: 0 0 30px rgba(34, 255, 106, 0.7);
    animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 25px rgba(34, 255, 106, 0.5); }
    50% { transform: scale(1.08); box-shadow: 0 0 45px rgba(34, 255, 106, 0.9); }
}

.aqi-row {
    display: flex; gap: 8px; justify-content: center;
    flex-wrap: wrap; margin: 1rem 0 1.4rem 0;
}
.aqi-pill {
    padding: 6px 12px; border-radius: 999px;
    font-size: .75rem; font-weight: 600; color: #0b1220;
}

[data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(34, 255, 106, 0.15);
    border-radius: 18px;
    padding: .9rem 1rem;
    backdrop-filter: blur(8px);
    margin-bottom: .6rem;
}

[data-testid="stChatInput"] {
    border-radius: 18px;
    border: 1px solid rgba(34, 255, 106, 0.4);
    background: #0d130f;
}

.stButton > button {
    width: 100%; border-radius: 16px;
    border: 1px solid rgba(34, 255, 106, 0.3);
    background: #0d130f;
    color: #eafff1; padding: .75rem 1rem; font-weight: 500;
    transition: all .2s ease;
}
.stButton > button:hover {
    background: #22ff6a;
    color: #04110a;
    border-color: #22ff6a;
    transform: translateY(-2px);
    box-shadow: 0 6px 22px rgba(34, 255, 106, 0.35);
}

.foot { text-align: center; color: #5f7d6c; font-size: .75rem; margin-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
<div class="hero">
  <div class="orb"></div>
  <h1>Lahore Smog Helper</h1>
  <p>Smog, hawa aur sehat ke baare mein kuch bhi puchein</p>
</div>
<div class="aqi-row">
  <span class="aqi-pill" style="background:#4ade80">0-50 Acha</span>
  <span class="aqi-pill" style="background:#facc15">51-100 Theek</span>
  <span class="aqi-pill" style="background:#fb923c">101-150 Sensitive</span>
  <span class="aqi-pill" style="background:#f87171">151-200 Kharab</span>
  <span class="aqi-pill" style="background:#c084fc">201-300 Bohat kharab</span>
  <span class="aqi-pill" style="background:#be123c; color:white">300+ Khatarnak</span>
</div>
""", unsafe_allow_html=True)

# ---------- BOT ----------
import os

api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

@st.cache_data(ttl=600)  # 10 minute tak data yaad rakho
def live_data():
    LAT, LON = 31.5204, 74.3587  # Lahore
    w = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT,
            "longitude": LON,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m",
            "timezone": "Asia/Karachi",
        },
        timeout=10,
    ).json()["current"]
    a = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": LAT,
            "longitude": LON,
            "current": "us_aqi,pm2_5,pm10",
            "timezone": "Asia/Karachi",
        },
        timeout=10,
    ).json()["current"]
    return (
        f"Live Lahore data from Open-Meteo (time {w['time']} Pakistan time): "
        f"temperature {w['temperature_2m']} C (feels like {w['apparent_temperature']} C), "
        f"humidity {w['relative_humidity_2m']}%, wind {w['wind_speed_10m']} km/h, "
        f"US AQI {a['us_aqi']}, PM2.5 {a['pm2_5']}, PM10 {a['pm10']}."
    )


def get_live_text():
    try:
        return live_data()
    except Exception:
        return None

system_prompt = """You are Lahore Smog Helper, a friendly and kind chatbot.

Language rule:
- Reply in the same language the user writes in.
- If the user writes in English, reply in simple English.
- If the user writes in Roman Urdu (Urdu in English letters), reply in simple Roman Urdu.
- If the user writes in Urdu script, reply in Urdu script.
- If the user asks you to switch language, switch.

Conversation rules:
- If someone asks how you are, reply warmly and ask how they are.
- Reply politely to greetings, thanks and goodbyes.
- Smog, air quality, health and safety are your main job, give very good answers on these.
- You may also answer other general questions briefly and directly.
- If a question is harmful or very strange, politely decline.

Length rule:
- Answer only as much as the question needs.
- Short question: 1-2 lines.
- Give long detail only if the user asks ("explain in detail").
- No extra advice, long lists or repetition.

You are not a doctor. Only for serious symptoms, tell the user to see a doctor."""
old_prompt = """Tum Lahore Smog Helper ho, ek dostana aur mehrbaan bot.
Roman Urdu mein aasan zubaan mein jawab do.

Baat cheet ke asool:
- Agar koi hal chaal pooche (jaise "kaise ho?"), to dostana andaaz mein jawab do aur aage poocho, jaise "Main theek hoon, shukriya! Aap sunaiye?"
- Salam, shukriya, khuda hafiz jaise alfaaz ka naram lehje mein jawab do.
- Smog, hawa ki quality, sehat aur hifazat tumhara khaas kaam hai, in sawalon ka behtareen jawab do.
- Doosre aam sawalon ka bhi chhota aur seedha jawab de sakte ho.
- Agar koi sawal bohat ajeeb ya nuqsandeh ho, to naram andaaz mein mana kar do.

Jawab ki lambai ka asool:
- Sirf utna jawab do jitna sawal poocha gaya hai.
- Chhote sawal ka jawab 1-2 lines mein do.
- Lambi tafseel tab do jab user khud kahe ("tafseel se batao").
- Extra salah, lambi list ya dohrao mat karo.

Tum doctor nahi ho. Sirf serious takleef ki soorat mein doctor se milne ka kaho."""

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None

# Naya sawal (type kiya hua ya button se)
sawal = st.chat_input("Apna sawal likhein...")
if st.session_state.pending:
    sawal = st.session_state.pending
    st.session_state.pending = None

# Pichli baatein dikhao
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Shuru mein sawalon ke buttons
suggestions = [
    "Mask kaunsa lun? 😷",
    "Bachon ke liye bahar jana safe hai?",
    "Ghar ki hawa kaise saaf karun?",
    "Aankhon mein jalan ho to kya karun?",
]
if not st.session_state.messages and not sawal:
    cols = st.columns(2)
    for i, q in enumerate(suggestions):
        if cols[i % 2].button(q, key=f"chip{i}"):
            st.session_state.pending = q
            st.rerun()

# Sawal ka jawab
if sawal:
    st.session_state.messages.append({"role": "user", "content": sawal})
    with st.chat_message("user"):
        st.markdown(sawal)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Soch raha hoon..."):
                live = get_live_text()
                if live:
                    live_rule = (
                        live
                        + "\nUse this live data when the user asks about today's weather, temperature or AQI. "
                        + "Tell them the AQI is an estimate from Open-Meteo and can differ slightly from ground sensors. "
                        + "Never invent numbers."
                    )
                else:
                    live_rule = (
                        "Live data is not available right now. If the user asks about current weather or AQI, "
                        "say you cannot fetch live data right now. Do not guess any numbers."
                    )
                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "system", "content": system_prompt + "\n\n" + live_rule}]
                    + st.session_state.messages,
                )
            jawab = response.choices[0].message.content
            st.markdown(jawab)
            st.session_state.messages.append({"role": "assistant", "content": jawab})
        except Exception:
            st.error("Kuch masla aa gaya, thori der baad dobara koshish karein.")
            st.session_state.messages.pop()

st.markdown(
    '<div class="foot">AI ke jawab ghalat ho sakte hain. Serious takleef par doctor se milein.</div>',
    unsafe_allow_html=True,
)
