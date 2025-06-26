# src/agents/config.py
"""エージェントシステムの設定モジュール

このモジュールは、エージェントの設定（モデル、ツール、説明文など）を定義します。
設定値を一元管理することで、コードの重複を減らし保守性を向上させます。
"""
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# デフォルトのLLMモデル（環境変数から取得）
DEFAULT_MODEL = os.environ.get("GEMINI_DEFAULT_MODEL")
SEARCH_MODEL = os.environ.get("GEMINI_SEARCH_MODEL")  # 検索用の軽量モデル

# 共通の設定値
RECIPE_DATABASE_ID = "personal-database-id"
ERROR_PREVENTION = (
    "missing required parametersエラーを防ぐため、内部で専用ツールを使用"
)

# エージェント設定
AGENT_CONFIG = {
    # ルートエージェント設定
    "root": {
        "name": "root_agent",
        "model": DEFAULT_MODEL,
        "prompt_key": "root",
        "description": "複数のサブエージェントを管理・調整するルートエージェント",
        "instruction": "複数のサブエージェントを管理・調整します。",
        "variables": {
            "recipe_database_id": RECIPE_DATABASE_ID,
            "error_prevention": ERROR_PREVENTION,
        },
    },
    # レシピエージェント設定
    "recipe_manager": {
        "name": "recipe_manager",
        "model": DEFAULT_MODEL,
        "prompt_key": "recipe_manager",
        "description": "レシピエージェントです。",
        "instruction": "レシピエージェントです。",
        "sub_agents": {
            "youtube_search_agent": {
                "name": "youtube_search_agent",
                "model": SEARCH_MODEL,
                "prompt_key": "youtube_search",
                "description": "YouTube検索エージェントです。",
                "instruction": "YouTubeで料理のレシピを検索します。",
            },
            "google_search_agent": {
                "name": "google_search_agent",
                "model": SEARCH_MODEL,
                "prompt_key": "google_search",
                "description": "Google検索エージェントです。",
                "instruction": "Googleで料理のレシピを検索します。",
            }
        }
    },
    #画像分析エージェント設定
    "image_analysis_manager": {
        "name": "image_analysis_manager", 
        "model": DEFAULT_MODEL,
        "prompt_key": "image_analysis_manager",
        "description": "画像情報の解析エージェントです。",
        "instruction": "レシート画像・食材画像から食材情報を抽出します。",
    },
    # 応答エージェント設定
    "response_manager": {
        "name": "response_manager",
        "model": DEFAULT_MODEL,
        "prompt_key": "response_manager",
        "description": "応答エージェントです。",
        "instruction": "応答エージェントです。",
        "sub_agents": {
            "line_response_agent": {
                "name": "line_response_agent",
                "model": DEFAULT_MODEL,
                "prompt_key": "line_response",
                "description": "LINE応答エージェントです。",
                "instruction": "LINE応答エージェントです。",
            }
        }
    },
}

# プロンプトパスのマッピング
PROMPT_MAPPING = {
    "root": "agents.root.main",
    "recipe_manager": "agents.recipe_manager.main",
    "youtube_search": "agents.youtube_search.main",
    "google_search": "agents.google_search.main",
    "response_manager": "agents.response_manager.main",
    "line_response": "agents.line_response_agent.main",
    "image_analysis_manager": "agents.image_analysis_manager.main",
}