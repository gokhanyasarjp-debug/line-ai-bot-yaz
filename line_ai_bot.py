import os
import random
import requests
import threading
import time
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (MessageEvent, TextMessage, TextSendMessage,
                             MemberJoinedEvent)
from groq import Groq

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "tRBDRPe24yG7J8ZQvKATurED2vIKl6+mDqpmPLRHFA28O9xAYXh1wTyH/wx7Id3wVwAQKH9aS4M456C3xUlXcxc+GJJ2TPDO4KW9RcMNr0TlraDqxQ7pQS5uN2S8EOcnqtzxS/QuN7H6/EXRroLwJwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET       = "2d7fa41df7847532829dd3e629dcb94c"
GROQ_API_KEY              = "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"
GROUP_ID                  = "C15ce6a2770453c0255912c829cab8572"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)
groq_client  = Groq(api_key=GROQ_API_KEY)

# Grup uyeleri - isim eslestirme
ISIMLER = {
    "Murat":   "Murat emmi",
    "murat":   "Murat emmi",
    "Ersin":   "Ersin abi",
    "ersin":   "Ersin abi",
    "Firat":   "kanka",
    "firat":   "kanka",
    "Fırat":   "kanka",
    "Emre":    "Emrecim",
    "emre":    "Emrecim",
    "Mert":    "Mertcim",
    "mert":    "Mertcim",
    "Cagatay": "Cagatayim",
    "cagatay": "Cagatayim",
    "Çağatay": "Cagatayim",
    "Gokhan":  "Patron",
    "gokhan":  "Patron",
}

def get_hitap(display_name):
    for isim, hitap in ISIMLER.items():
        if isim.lower() in display_name.lower():
            return hitap
    return display_name

BOT_PERSONA = """
Sen HaNofficial adinda bir asistansin.
Sahibinin adi Gokhan, ona her zaman "Patron" diye hitap edersin.
Gruptaki diger uyelere asagidaki sekilde hitap edersin:
- Murat = Murat emmi
- Ersin = Ersin abi
- Firat = kanka
- Emre = Emrecim
- Mert = Mertcim
- Cagatay = Cagatayim
Patron ne derse onu yaparsın, kendi kararini vermezsin.
Turkce konusursun, samimi ve sadik bir asistansin.
Kisa ve net cevaplar verirsin.
Emoji kullanabilirsin ama abartma.
Patron disindaki kisilere nazik ama onlara da isimleriyle hitap edersin.
"""

conversation_history = {}
MAX_HISTORY = 20

# ─────────────────────────────────────────
#  2 SAATTE BIR NABER MILLET
# ─────────────────────────────────────────
def send_periodic_message():
    while True:
        time.sleep(2 * 60 * 60)
        try:
            mesajlar = [
                "Naber millet! 👋 Nasil gidiyor?",
                "Hey millet, ne var ne yok? 😄",
                "Selam! Hayat nasil? 🙌",
                "Naber! Umarim iyisinizdir 😊",
                "Hey! Keyifler nasil? 🎉"
            ]
            mesaj = random.choice(mesajlar)
            line_bot_api.push_message(GROUP_ID, TextSendMessage(text=mesaj))
        except Exception as e:
            print(f"[PERIYODIK HATA] {e}")

t = threading.Thread(target=send_periodic_message, daemon=True)
t.start()

# ─────────────────────────────────────────
#  HAVA DURUMU
# ─────────────────────────────────────────
def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=3&lang=tr"
        r = requests.get(url, timeout=5)
        return r.text.strip()
    except:
        return "Hava durumu alinamadi. 🌫️"

# ─────────────────────────────────────────
#  DOVİZ KURU
# ─────────────────────────────────────────
def get_exchange():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        data = r.json()
        usd_try = data["rates"]["TRY"]
        eur_usd = data["rates"]["EUR"]
        eur_try = usd_try / eur_usd
        return (f"💵 1 USD = {usd_try:.2f} TL\n"
                f"💶 1 EUR = {eur_try:.2f} TL")
    except:
        return "Doviz bilgisi alinamadi. 📉"

# ─────────────────────────────────────────
#  WEBHOOK
# ─────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ─────────────────────────────────────────
#  GRUBA KATILAN KARŞİLA
# ─────────────────────────────────────────
@handler.add(MemberJoinedEvent)
def handle_join(event):
    try:
        for member in event.joined.members:
            profile = line_bot_api.get_group_member_profile(
                event.source.group_id, member.user_id)
            name = profile.display_name
            hitap = get_hitap(name)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"Hos geldin {hitap}! 👋 Gruba katildigin icin memnunuz 😊")
            )
    except Exception as e:
        print(f"[JOIN HATA] {e}")

# ─────────────────────────────────────────
#  MESAJ İŞLE
# ─────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id      = event.source.user_id
    user_message = event.message.text.strip()

    # Gonderen kişinin adını al
    try:
        if event.source.type == "group":
            profile = line_bot_api.get_group_member_profile(GROUP_ID, user_id)
        else:
            profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
        hitap = get_hitap(display_name)
    except:
        display_name = "Kullanici"
        hitap = "Kullanici"

    # Gruba mesaj gonder
    if user_message.lower().startswith("/gonder "):
        mesaj = user_message[8:]
        line_bot_api.push_message(GROUP_ID, TextSendMessage(text=mesaj))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ Mesaj gruba gonderildi!")
        )
        return

    # Hava komutu
    if user_message.lower().startswith("/hava"):
        parts = user_message.split(" ", 1)
        city = parts[1] if len(parts) > 1 else "Istanbul"
        reply = get_weather(city)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # Doviz komutu
    if user_message.lower().startswith("/doviz"):
        reply = get_exchange()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # Grupta sadece ismi gecince cevap ver
    if event.source.type == "group":
        if "HaNofficial" not in user_message and "hanofficial" not in user_message.lower():
            return

    if user_id not in conversation_history:
        sistem = BOT_PERSONA + f"\nSimdi {hitap} ile konusuyorsun."
        conversation_history[user_id] = [{"role": "system", "content": sistem}]

    history = conversation_history[user_id]
    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY * 2 + 1:
        history = [history[0]] + history[-(MAX_HISTORY * 2):]
        conversation_history[user_id] = history

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history,
            max_tokens=500
        )
        reply_text = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": reply_text})
    except Exception as e:
        reply_text = f"Hata: {str(e)[:200]}"
        print(f"[AI HATA] {e}")

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@app.route("/", methods=["GET"])
def health():
    return "HaNofficial AI Bot calisiyor!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
