"""エージェント実行モジュール

このモジュールは、エージェントの実行と応答の取得を担当します。
ランナーを使ってエージェントを実行し、応答を処理する機能を提供します。
"""

from typing import Optional

from google.adk.runners import Runner
from google.genai import types

from utils.logging import setup_cloud_logging

logger = setup_cloud_logging("executor")


class AgentExecutor:
    """エージェント実行クラス

    ランナーを使用してエージェントを実行し、応答を処理します。
    """

    def __init__(self, runner: Runner):
        """初期化

        Args:
            runner: エージェント実行用のランナー
        """
        self.runner = runner

    async def execute_and_get_response(
        self,
        message: str,
        user_id: str,
        session_id: str,
        content: types.Content,
        image_data: Optional[bytes] = None,
    ) -> str:
        """エージェントを実行し応答を取得

        Args:
            message: オリジナルのメッセージ（ログ用）
            user_id: ユーザーID
            session_id: セッションID
            content: Content型のメッセージ
            image_data: 画像データ（ログ用）

        Returns:
            エージェントからの最終応答
        """
        try:
            # ログ出力
            self._log_execution_start(message, image_data)

            # エージェント実行
            events_async = self.runner.run_async(
                session_id=session_id, 
                user_id=user_id, 
                new_message=content,
            )

            # 応答を取得
            final_response = None
            async for event in events_async:
                # エラーチェック
                if hasattr(event, 'finish_reason') and event.finish_reason == 'MALFORMED_FUNCTION_CALL':
                    error_msg = f"申し訳ありません。エージェントが未定義の機能を呼び出そうとしました。"
                    logger.error(f"Agent error: {event.finish_message}")
                    return error_msg

                # 最終応答の処理
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text.strip()
                    logger.info(f"Received final response from agent: {final_response}")
                    break

            return final_response if final_response else "応答を取得できませんでした。"

        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            if "Timed out while waiting for response" in str(e):
                return "申し訳ありません。処理に時間がかかりすぎています。\n\n考えられる原因：\n- サーバーの負荷が高い\n- 外部APIの応答が遅い\n- 処理するデータ量が多い\n\nしばらく時間をおいてから再試行してください。"
            return f"申し訳ありません。エラーが発生しました: {str(e)}"

    def _log_execution_start(
        self, message: str, image_data: Optional[bytes]
    ) -> None:
        """エージェント実行開始時のログ出力

        Args:
            message: ユーザーメッセージ
            image_data: 画像データ（オプション）
        """
        if image_data:
            logger.info(f"Starting agent execution with image and message: {message}")
        else:
            logger.info(f"Starting agent execution with message: {message}")

    # 以下、将来の拡張用に既存のコードをコメントアウトで保持

    # async def _process_final_response(
    #     self, event, all_responses: List[str], step_count: int
    # ) -> Optional[Tuple[str, List[str], int]]:
    #     """最終応答候補を処理

    #     Args:
    #         event: イベントオブジェクト
    #         all_responses: これまでの応答リスト
    #         step_count: 現在のステップカウント

    #     Returns:
    #         処理結果のタプル (最終応答, 応答リスト, ステップカウント)
    #         または None（最終応答候補ではない場合）
    #     """
    #     if not (
    #         event.is_final_response() and event.content and event.content.parts
    #     ):
    #         return None

    #     current_response = event.content.parts[0].text

    #     # Sequential Agentの中間応答を検出
    #     if is_intermediate_response(
    #         event.author, current_response
    #     ):
    #         logger.info(
    #             f"Sequential intermediate response from {event.author}"
    #         )
    #         all_responses.append(current_response)
    #         step_count += 1
    #         return ("", all_responses, step_count)

    #     # 真の最終応答かどうかを判定
    #     if ResponseProcessor.is_final_response(
    #         event.author, current_response, step_count
    #     ):
    #         return (current_response, all_responses, step_count)
    #     else:
    #         logger.info(
    #             f"Received response from {event.author}, continuing..."
    #         )
    #         all_responses.append(current_response)
    #         return ("", all_responses, step_count)
    # def is_intermediate_response(author: str, response: str) -> bool:
    #     """Sequential Agentの中間応答かどうかを判定

    #     Args:
    #         author: 応答者（エージェント）名
    #         response: 応答テキスト

    #     Returns:
    #         中間応答であればTrue、そうでなければFalse
    #     """
    #     # JSON形式のみの応答は中間結果の可能性が高い
    #     if response.strip().startswith(
    #         "```json"
    #     ) and response.strip().endswith("```"):
    #         return True

    #     # 特定のエージェント名パターンで中間応答を検出
    #     for pattern in INTERMEDIATE_PATTERNS:
    #         if pattern in response:
    #             return True

    #     # 短すぎる応答（JSON断片など）
    #     if len(response.strip()) < 50 and "```" in response:
    #         return True

    #     return False
    # def _handle_fallback_response(self, all_responses: List[str]) -> str:
    #     """フォールバック応答を取得

    #     最終応答がない場合に、代替の応答を返します。

    #     Args:
    #         all_responses: 収集されたすべての応答

    #     Returns:
    #         フォールバック応答
    #     """
    #     if all_responses:
    #         final_response = all_responses[-1]
    #         logger.info("Using last collected response as final response")
    #         return final_response
    #     else:
    #         logger.warning("No responses collected from agent")
    #         return "応答を取得できませんでした。"