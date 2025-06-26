# filepath: /workspace/src/agents/root_agent.py
"""シンプルなエージェント定義モジュール"""

from contextlib import AsyncExitStack
from typing import Tuple

from google.adk.agents.llm_agent import LlmAgent
from agents.agent_manager import AgentManager
from agents.config import AGENT_CONFIG
from utils.logging import setup_cloud_logging
from agents.prompt_manager import PromptManager

# ロガーを設定
logger = setup_cloud_logging("root_agent")

# グローバル変数
_root_agent = None
_exit_stack = AsyncExitStack()

async def create_agent() -> Tuple[LlmAgent, AsyncExitStack]:
    """シンプルなエージェントを作成する

    Returns:
        Tuple[LlmAgent, AsyncExitStack]: エージェントとリソース管理用のexitスタック
    """
    global _root_agent, _exit_stack

    # すでに作成済みの場合はそれを返す
    if _root_agent is not None:
        return _root_agent, _exit_stack

    try:
        prompt_manager = PromptManager()
        prompts = prompt_manager.get_all_prompts()

        factory = AgentManager(prompts=prompts, config=AGENT_CONFIG)

        # すべての標準エージェントを作成
        agents = factory.create_all_standard_agents()

        # ルートエージェントを作成
        _root_agent = factory.create_root_agent(agents)

    except Exception as e:
        logger.error(f"エージェント作成中にエラーが発生: {e}")
        raise

    return _root_agent, _exit_stack