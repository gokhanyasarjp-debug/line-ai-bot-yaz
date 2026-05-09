"""
Line AI Bot - Claude Destekli
================================
Gelen Line mesajlarına Claude AI ile otomatik cevap verir.

Gereksinimler:
  pip install flask line-bot-sdk anthropic

Render.com'da çalıştırmak için:
  - Bu dosyayı GitHub'a yükle
  - Render.com'da Web Service oluştur
  - Environment Variables ekle
"""

import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import anthropic

app = Flask(__name__)

# ─────────────────────────────────────────
#  AYARLAR — Render.com'da Environment Variables olarak ekle
# ─────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")
ANTHROPIC_API_KEY         = os.environ.get("ANTHROPIC_API_KEY", "")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)
ai_client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────
#  BOT KİŞİLİĞİ — istediğin gibi özelleştir
# ─────────────────────────────────────────
BOT_PERSONA = """
Sen yardımsever, samimi ve zeki bir asistansın.
Türkçe mesajlara Türkçe, diğer dillere o dilde cevap ver.
Kısa ve net cevaplar ver, gereksiz uzatma.
Emoji kullanabilirsin ama abartma.
"""

# Her kullanıcının sohbet geçmişini sakla (bellekte)
conversation_history = {}
MAX_HISTORY = 10  # En fazla kaç mesaj hatırlasın

# ─────────────────────────────────────────
#  WEBHOOK — Line'dan gelen mesajları al
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
#  MESAJ OLAYINI İŞLE
# ─────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id      = event.source.user_id
    user_message = event.message.text

    print(f"[{user_id}] Gelen: {user_message}")

    # Sohbet geçmişini al veya oluştur
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]
    history.append({"role": "user", "content": user_message})

    # Geçmişi sınırla
    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]
        conversation_history[user_id] = history

    # Claude AI'dan cevap al
    try:
        response = ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=BOT_PERSONA,
            messages=history
        )
        reply_text = response.content[0].text

        # Cevabı geçmişe ekle
        history.append({"role": "assistant", "content": reply_text})

    except Exception as e:
        reply_text = "Üzgünüm, şu an cevap veremiyorum. Lütfen tekrar dene. 🙏"
        print(f"[AI HATA] {e}")

    print(f"[{user_id}] Cevap: {reply_text}")

    # Line'a cevap gönder
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
