import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from groq import Groq

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "tRBDRPe24yG7J8ZQvKATurED2vIKl6+mDqpmPLRHFA28O9xAYXh1wTyH/wx7Id3wVwAQKH9aS4M456C3xUlXcxc+GJJ2TPDO4KW9RcMNr0TlraDqxQ7pQS5uN2S8EOcnqtzxS/QuN7H6/EXRroLwJwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET       = "2d7fa41df7847532829dd3e629dcb94c"
GROQ_API_KEY              = "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"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)
groq_client  = Groq(api_key=GROQ_API_KEY)

BOT_PERSONA = "Sen yardımsever, samimi ve zeki bir asistansın. Türkçe mesajlara Türkçe, diğer dillere o dilde cevap ver. Kısa ve net cevaplar ver. Emoji kullanabilirsin ama abartma."

conversation_history = {}
MAX_HISTORY = 10

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id      = event.source.user_id
    user_message = event.message.text

    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": BOT_PERSONA}]

    history = conversation_history[user_id]
    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY * 2 + 1:
        history = [history[0]] + history[-(MAX_HISTORY * 2):]
        conversation_history[user_id] = history

    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
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
    return "Line AI Bot calisiyor!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
