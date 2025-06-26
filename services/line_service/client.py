"""LINEメッセージングAPI操作モジュール

このモジュールは、LINE Messaging APIとの通信を担当します。
メッセージの送信や受信、画像データの取得などの機能を提供します。
"""

from typing import TYPE_CHECKING, List

from linebot.v3 import WebhookParser
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent

from services.line_service.constants import get_line_config
from utils.logging import setup_cloud_logging

if TYPE_CHECKING:
    from services.line_service.handler import LineEventHandler

logger = setup_cloud_logging("line_client")


class LineClient:
    """LINE APIクライアントラッパークラス

    LINE Messaging APIへのアクセスを簡略化するためのラッパークラス。
    設定の読み込みやエラー処理を集約しています。
    """

    def __init__(self):
        """LINE APIクライアントの初期化"""
        # LINE API設定を取得
        channel_access_token, channel_secret = get_line_config()

        # 設定を作成
        self.configuration = Configuration(access_token=channel_access_token)
        self.parser = WebhookParser(channel_secret)

        logger.info("LINE client initialized")

    def parse_webhook_events(self, body: str, signature: str) -> list:
        """Webhookボディからイベントをパースする

        Args:
            body: Webhookリクエストボディ
            signature: X-Line-Signatureヘッダー値

        Returns:
            list: パースされたイベントのリスト

        Raises:
            Exception: パースに失敗した場合
        """
        try:
            events = self.parser.parse(body, signature)
            return events
        except Exception as e:
            logger.exception(f"Failed to parse webhook events: {e}")
            raise

    def create_api_client(self) -> ApiClient:
        """APIクライアントを作成

        Returns:
            ApiClient: LINE Messaging API クライアント
        """
        return ApiClient(self.configuration)

    def reply_text(self, reply_token: str, text: str) -> None:
        """テキストメッセージで返信

        Args:
            reply_token: 返信用トークン
            text: 送信するテキスト
        """
        try:
            with self.create_api_client() as api_client:
                line_api = MessagingApi(api_client)
                line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=text)],
                    )
                )
            logger.info(f"Successfully sent reply with text: {text[:50]}...")
        except Exception as e:
            logger.exception(f"Failed to reply with text: {e}")
            raise

    def get_message_content(self, message_id: str) -> bytes:
        """メッセージの画像コンテンツを取得
        Args:
            message_id: メッセージID
        Returns:
            bytes: 画像データ
        """
        try:
            with self.create_api_client() as blob_api_client:
                blob_api = MessagingApiBlob(blob_api_client)
                image_content = blob_api.get_message_content(message_id)
                logger.info(
                    f"Successfully retrieved image content: {message_id}"
                )
                return image_content
        except Exception as e:
            logger.exception(f"Failed to retrieve image content: {e}")
            raise

    def push_text(self, user_id: str, text: str) -> None:
        """ユーザーにテキストメッセージをプッシュ送信

        Args:
            user_id: 送信先のユーザーID
            text: 送信するテキスト
        """
        try:
            with self.create_api_client() as api_client:
                line_api = MessagingApi(api_client)
                line_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=text)],
                    )
                )
            logger.info(f"Successfully pushed message to {user_id}: {text[:50]}...")
        except Exception as e:
            logger.exception(f"Failed to push message: {e}")
            raise

    async def handle_events(self, events: List[MessageEvent]) -> None:
        """イベントを処理する

        Args:
            events: 処理するイベントのリスト
        """
        from services.line_service.handler import LineEventHandler

        handler = LineEventHandler(self)
        for event in events:
            if isinstance(event, MessageEvent):
                await handler.handle_event(event)
            else:
                logger.info(f"Unsupported event type: {type(event)}")