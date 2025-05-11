from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
import uvicorn

# 環境変数の読み込み
load_dotenv()

app = FastAPI()

# LINEの設定
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=["POST"])
async def callback(request: Request):
    # リクエストヘッダーからX-Line-Signatureを取得
    signature = request.headers.get('X-Line-Signature', '')

    # リクエストボディを取得
    body = await request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")
    try:
        # 署名を検証し、問題なければhandleに定義されている関数を呼び出す
        handler.handle(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return {"status": "OK"}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # メッセージを返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Hello World")
    )

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 