import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# ─────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN = "C8eyVgzqUSSIMz3sYFB93/agk+7KoPB+Nkr6f7ZE8NhqceSbzfD6dUCEabCKgWTxVwAQKH9aS4M456C3xUIXcxc+GJJ2TPDO4KW9RcMNr0T/1VUqQ7d1rk30tckIAAFo9SrOtqzMCNq1oADwabljMgdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET       = "2d7fa41df7847532829dd3e629dcb94c"
GEMINI_API_KEY            = "AIzaSyDSAC5jciZdG559itHgBixH5zxEdiCKndI"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ─────────────────────────────────────────
#  BOT KİŞİLİĞİ
# ─────────────────────────────────────────
BOT_PERSONA = """
Sen yardımsever, samimi ve zeki bir asistansın.
Türkçe mesajlara Türkçe, diğer dillere o dilde cevap ver.
Kısa ve net cevaplar ver, gereksiz uzatma.
Emoji kullanabilirsin ama abartma.
"""

# Sohbet geçmişi
conversation_history = {}
MAX_HISTORY = 10

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
#  MESAJ İŞLE
# ─────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id      = event.source.user_id
    user_message = event.message.text

    print(f"[{user_id}] Gelen: {user_message}")

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]
    history.append(f"Kullanıcı: {user_message}")

    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]
        conversation_history[user_id] = history

    try:
        prompt = BOT_PERSONA + "\n\nSohbet geçmişi:\n" + "\n".join(history) + "\n\nAsistan:"
        response = model.generate_content(prompt)
        reply_text = response.text.strip()
        history.append(f"Asistan: {reply_text}")
    except Exception as e:
        reply_text = "Üzgünüm, şu an cevap veremiyorum. Lütfen tekrar dene. 🙏"
        print(f"[AI HATA] {e}")

    print(f"[{user_id}] Cevap: {reply_text}")

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# ─────────────────────────────────────────
#  SAĞLIK KONTROLÜ
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return "✅ Line AI Bot çalışıyor!", 200

# ─────────────────────────────────────────
#  BAŞLAT
# ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
