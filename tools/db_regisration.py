from utils.logging import setup_cloud_logging
from google.adk.tools.tool_context import ToolContext

logger = setup_cloud_logging("db_regisration")

def save_session(session_id: str, message: str, tool_context: ToolContext) -> dict:
    """会話をセッションに保存"""
    sessions = tool_context.state.get("sessions", {})
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append(message)
    tool_context.state["sessions"] = sessions
    return {"status": "success", "message": "Session saved"}

def get_session(session_id: str, tool_context: ToolContext) -> dict:
    """セッションの会話履歴を取得"""
    sessions = tool_context.state.get("sessions", {})
    history = sessions.get(session_id, [])
    return {"history": history}
