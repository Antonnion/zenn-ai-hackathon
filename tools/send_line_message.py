import os
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

def send_line_message(**kwargs):
    # 環境変数からチャンネルアクセストークンを取得
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not channel_access_token:
        raise ValueError("LINE_CHANNEL_ACCESS_TOKEN environment variable is not set")
        
    MCPToolset(
                connection_params=StdioServerParameters( 
                command= 'npx' , 
                args=[ "-y" , "@line/line-bot-mcp-server" ], 
                env={ 
                    "CHANNEL_ACCESS_TOKEN" : channel_access_token, 
                    "DESTINATION_USER_ID" : kwargs["user_id"]
                },
                timeout=60,
            )
        )