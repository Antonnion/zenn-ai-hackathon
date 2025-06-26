import logging
import asyncio
import os
from fastapi import FastAPI, Request
import uvicorn
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
from linebot.v3 import WebhookParser
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService, Session
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.tools import load_memory
from google.cloud import logging as cloud_logging
from google.genai.types import Content, Part
from services.line_service.client import LineClient
from services.line_service.handler import LineEventHandler
from utils.logging import setup_cloud_logging

# ロガーを設定
logger = setup_cloud_logging("main")

# FastAPIの設定
app = FastAPI()

# LINEクライアントの準備
line_client = LineClient()
line_handler = LineEventHandler(line_client)

async def process_message_and_reply(body: str, signature: str):
    try:
        # イベントのパース
        events = line_client.parse_webhook_events(body, signature)
        
        # 各イベントを処理
        for event in events:
            if isinstance(event, MessageEvent):
                await line_handler.handle_event(event)

    except Exception as e:
        logging.error(f"Error in process_events: {e}")

@app.post("/callback")
async def callback(request: Request):
    # リクエストボディとシグネチャの取得
    body = await request.body()
    body_text = body.decode("utf-8")
    signature = request.headers.get("X-Line-Signature", "")
    
    # 非同期でメッセージ処理
    await process_message_and_reply(body_text, signature)
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
