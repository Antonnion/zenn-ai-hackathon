"""LINEイベント処理モジュール

このモジュールは、LINEからのWebhookイベントを処理する機能を提供します。
各種メッセージタイプに対する処理を担当します。
"""

from typing import Optional

from linebot.v3.webhooks import (
    ImageMessageContent,
    MessageEvent,
    TextMessageContent,
)
from services.line_service.client import LineClient
from services.line_service.constants import ERROR_MESSAGE
from services.agent_service_impl import call_agent_async, call_agent_with_image_async
from utils.logging import setup_cloud_logging

logger = setup_cloud_logging("line_handler")


class LineEventHandler:
    """LINEイベント処理クラス

    LINEからのイベントを処理するためのクラスです。
    各種メッセージタイプに応じた処理を提供します。
    """

    def __init__(self, line_client: Optional[LineClient] = None):
        """初期化

        Args:
            line_client: LINE APIクライアント（未指定時は新規作成）
        """
        self.line_client = line_client or LineClient()

    async def handle_text_message(
        self, event: MessageEvent, text_content: TextMessageContent
    ) -> None:
        """テキストメッセージの処理

        Args:
            event: LINEメッセージイベント
            text_content: テキストメッセージ内容
        """
        user_id = event.source.user_id
        reply_token = event.reply_token

        logger.info(
            f"Processing text message from {user_id}: {text_content.text}"
        )

        try:
            # エージェントに問い合わせ
            reply_text = await call_agent_async(
                text_content.text,
                user_id=user_id,
            )
            reply_text = reply_text.rstrip("\n")

            # 返信を送信
            self.line_client.reply_text(reply_token, reply_text)

        except Exception as e:
            logger.exception(f"Error processing text message: {e}")
            self._handle_error_reply(reply_token)
            
    async def handle_image_message(
        self, event: MessageEvent, image_content: ImageMessageContent
    ) -> None:
        """画像メッセージの処理

        Args:
            event: LINEメッセージイベント
            image_content: 画像メッセージ内容
        """
        user_id = event.source.user_id
        reply_token = event.reply_token
        
        message_id = image_content.id

        logger.info(f"[画像解析フロー] 処理開始: user_id={user_id}, message_id={message_id}")
        
        # 処理開始を通知
        self.line_client.reply_text(reply_token, "📸 画像を解析中です。しばらくお待ちください...")
        
        try:
            # 画像データを取得
            image_data = self.line_client.get_message_content(message_id)
            
            # プッシュメッセージで途中経過を通知
            self.line_client.push_text(
                user_id, 
                "⚙️ 食材を抽出中... 画像内の食材を識別しています。"
            )
            
            # エージェントに問い合わせ
            reply_text = await call_agent_with_image_async(
                message="この画像(レシート画像・食材画像）から食材を抽出して、食材をリスト形式で返してください",
                image_data=image_data,
                image_mime_type="image/jpeg",
                user_id=user_id,
            )

            # 結果を送信
            self.line_client.push_text(user_id, reply_text)

        except Exception as e:
            # エラーメッセージを送信
            error_message = f"😓 申し訳ありません。画像処理中にエラーが発生しました。\n時間を空けて再度、画像をアップロードしてください。\nエラー詳細: {str(e)[:100]}..."
            self.line_client.push_text(user_id, error_message)

    async def handle_event(self, event: MessageEvent) -> None:
        """イベントハンドラのエントリーポイント

        Args:
            event: LINEメッセージイベント
        """
        try:
            # メッセージタイプに応じて処理を分岐
            if isinstance(event.message, TextMessageContent):
                await self.handle_text_message(event, event.message)
            elif isinstance(event.message, ImageMessageContent):
                await self.handle_image_message(event, event.message)
            else:
                logger.info(f"Unsupported message type: {type(event.message)}")
                self.line_client.reply_text(
                    event.reply_token,
                    "申し訳ございません。このメッセージタイプには対応していません。",
                )

        except Exception as e:
            logger.exception(f"Error in handle_event: {e}")
            self._handle_error_reply(event.reply_token)

    def _handle_error_reply(self, reply_token: str) -> None:
        """エラー時の返信処理

        Args:
            reply_token: 返信用トークン
        """
        try:
            self.line_client.reply_text(reply_token, ERROR_MESSAGE)
        except Exception as e:
            logger.exception(f"Failed to send error message: {e}")