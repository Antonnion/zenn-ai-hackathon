"""シンプルなエージェントサービスモジュール"""
import sqlalchemy
import os
from typing import Optional
from sqlalchemy.orm import Session
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from dotenv import load_dotenv
from services.agent_service.session_manager import SessionManager
from services.agent_service.message_handler import MessageHandler
from services.agent_service.executor import AgentExecutor
from services.agent_service.constants import APP_NAME
from agents.root_agent import create_agent
from utils.logging import setup_cloud_logging

# 環境変数の読み込み
load_dotenv()

# ロガーを設定
logger = setup_cloud_logging("agent_service")

class AgentService:
    """シンプルなエージェントサービスクラス"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Cloud SQL接続を行う場合の設定
            # 環境変数からDB接続情報を取得
            
            # db_user = os.environ.get("DB_USER", "postgres")
            # db_pass = os.environ.get("DB_PASS")
            # db_name = os.environ.get("DB_NAME", "recipe_db")
            # instance_connection_name = os.environ.get("DB_INSTANCE_CONNECTION_NAME")
            
            # if not all([db_pass, instance_connection_name]):
            #     logger.warning("一部のDB接続情報が環境変数に設定されていません")
            # db_url = sqlalchemy.engine.URL.create(
            #     drivername="postgresql+psycopg2",
            #     username=db_user,
            #     password=db_pass,
            #     database=db_name,
            #     query={
            #         "host": f"/cloudsql/{instance_connection_name}"
            #     }
            # )
            
            self.session_service = InMemorySessionService()
            logger.info(f"session_service: {self.session_service}")

            self.artifacts_service = InMemoryArtifactService()
            # コンポーネントの初期化
            self.session_manager = SessionManager(self.session_service)
            self.message_handler = MessageHandler()

            # エージェント関連
            self.root_agent = None
            self.exit_stack = None
            self.runner = None
            self.executor = None

            # 初期化完了
            self._initialized = True

    async def init_agent(self) -> None:
        if self.root_agent is None:
            try:
                self.root_agent, self.exit_stack = await create_agent()
                self.runner = Runner(
                    app_name=APP_NAME,
                    agent=self.root_agent,
                    artifact_service=self.artifacts_service,
                    session_service=self.session_service,
                )
                self.executor = AgentExecutor(self.runner)

                logger.info("Agent initialized successfully")
            except Exception as e:
                logger.error(f"エージェントの初期化に失敗しました: {e}")
                raise

    async def call_agent_text(
        self, message: str, user_id: str, session_id: Optional[str] = None
    ) -> str:
        logger.info(f"テキストメッセージの処理を開始: user_id={user_id}, message={message[:100]}...")
        return await self._call_agent_internal(
            message=message,
            user_id=user_id,
            session_id=session_id,
            image_data=None,
            image_mime_type=None,
        )

    async def call_agent_with_image(
        self,
        message: str,
        image_data: bytes,
        image_mime_type: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> str:
        """画像付きメッセージを送信して応答を取得"""
        logger.info(f"画像付きメッセージの処理を開始: user_id={user_id}, message={message[:100]}...")
        return await self._call_agent_internal(
            message=message,
            user_id=user_id,
            session_id=session_id,
            image_data=image_data,
            image_mime_type=image_mime_type,
        )

    async def _call_agent_internal(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
        image_data: Optional[bytes] = None,
        image_mime_type: Optional[str] = None,
    ) -> str:
        await self.init_agent()
        # セッションを管理
        session_id = await self.session_manager.get_or_create_session(
            user_id, session_id
        )
        # メッセージをContent型に変換
        content = self.message_handler.create_message_content(
            message, image_data, image_mime_type
        )

        # エージェントを実行して応答を取得
        logger.info(f"エージェントを実行して応答を取得: message={message[:100]}...")
        return await self.executor.execute_and_get_response(
            message, user_id, session_id, content, image_data
        )

    async def cleanup_resources(self) -> None:
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.error(f"リソースのクリーンアップ中にエラーが発生: {e}")

# シングルトンインスタンスをエクスポート
_agent_service = AgentService()

# 後方互換性のための関数インターフェース
async def init_agent():
    await _agent_service.init_agent()
    return _agent_service.root_agent

async def call_agent_async(
    message: str, user_id: str, session_id: Optional[str] = None
) -> str:
    return await _agent_service.call_agent_text(message, user_id, session_id)

async def call_agent_with_image_async(
    message: str,
    image_data: bytes,
    image_mime_type: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> str:
    """画像付きメッセージをエージェントに送信し、応答を返す"""
    return await _agent_service.call_agent_with_image(
        message, image_data, image_mime_type, user_id, session_id
    )

async def cleanup_resources():
    await _agent_service.cleanup_resources()