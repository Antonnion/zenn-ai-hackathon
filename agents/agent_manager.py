"""エージェントのガーデン

このモジュールはエージェントを生成するためのガーデンを提供します。
"""

from typing import Dict

from google.adk.agents import Agent
from google.adk.agents.llm_agent import LlmAgent
from utils.logging import setup_cloud_logging
from tools.youtube_tools import get_recipe_from_youtube
from tools.send_line_message import send_line_message
from google.adk.tools import google_search
from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
# ロガー
logger = setup_cloud_logging("agent_manager")

class AgentManager:
    """エージェントのガーデン

    エージェントの生成ロジックをカプセル化して提供します。
    """

    def __init__(self, prompts: Dict, config: Dict):
        self.prompts = prompts
        self.config = config
        # 共通変数を追加
        self.common_variables = {
            "required_fields": "名前、材料、手順",
        }

    def recipe_manager(self) -> ParallelAgent:
        # 設定からサブエージェント情報を取得
        recipe_manager_config = self.config["recipe_manager"]
        youtube_search_agent_config = recipe_manager_config["sub_agents"]["youtube_search_agent"]
        google_search_agent_config = recipe_manager_config["sub_agents"]["google_search_agent"]

        # 1. Youtube Search Agent
        youtube_search_instruction = self.prompts[youtube_search_agent_config["prompt_key"]]
        youtube_search_agent = LlmAgent(
            name=youtube_search_agent_config["name"],
            model=youtube_search_agent_config["model"],
            description=youtube_search_agent_config["description"],
            instruction=youtube_search_instruction,
            tools=[
                get_recipe_from_youtube,
            ],
        )

        # 2. Google Search Agent
        google_search_instruction = self.prompts[google_search_agent_config["prompt_key"]]
        google_search_agent = LlmAgent(
            name=google_search_agent_config["name"],
            model=google_search_agent_config["model"],
            description=google_search_agent_config["description"],
            instruction=google_search_instruction,
            tools=[google_search],
        )

        return ParallelAgent(
            name="recipe_manager",
            sub_agents=[
                youtube_search_agent,
                google_search_agent,
            ],
            description="Google検索エージェントとYouTube検索エージェントを並列検索するパイプラインを実行します。",
        )

    def image_analysis_manager(self) -> LlmAgent:
        """画像分析エージェントを作成"""
        cfg = self.config["image_analysis_manager"]
        
        # 画像分析エージェントの設定を取得
        image_analysis_manager_instruction = self.prompts[cfg["prompt_key"]]
        
        return LlmAgent(
            name=cfg["name"],
            model=cfg["model"],
            description=cfg["description"],
            instruction=image_analysis_manager_instruction,
            tools=[],
        )

    def response_manager(self) -> ParallelAgent:
        response_manager_config = self.config["response_manager"]
        line_response_agent_config = response_manager_config["sub_agents"]["line_response_agent"]

        # 1. Line Response Agent
        line_response_instruction = self.prompts[line_response_agent_config["prompt_key"]]
        line_response_agent = LlmAgent(
            name=line_response_agent_config["name"],
            model=line_response_agent_config["model"],
            description=line_response_agent_config["description"],
            instruction=line_response_instruction,
            tools=[
                send_line_message,
            ],
        )

        return ParallelAgent(
            name="response_management",
            sub_agents=[
                line_response_agent,
            ],
            description="LINE応答エージェントを管理するパイプラインを実行します。",
        )

    def create_all_standard_agents(self) -> Dict[str, LlmAgent]:

        # 各エージェントを作成
        recipe_manager_agent = self.recipe_manager()
        response_manager_agent = self.response_manager()
        image_analysis_manager_agent = self.image_analysis_manager()

        # エージェントをディクショナリにまとめて返却
        return {
            "recipe_manager_agent": recipe_manager_agent,
            "response_manager_agent": response_manager_agent,
            "image_analysis_manager_agent": image_analysis_manager_agent,
        }
    
    def create_root_agent(self, sub_agents: Dict[str, Agent]) -> LlmAgent:
        """ルートエージェントを作成"""
        cfg = self.config["root"]
        
        # プロンプトからinstructionを取得
        root_instruction = self.prompts[cfg["prompt_key"]]
        
        return LlmAgent(
            name=cfg["name"],
            model=cfg["model"],
            instruction=root_instruction,
            description=cfg["description"],
            sub_agents=[
                sub_agents["recipe_manager_agent"],
                sub_agents["response_manager_agent"],
                sub_agents["image_analysis_manager_agent"],
            ]
        )