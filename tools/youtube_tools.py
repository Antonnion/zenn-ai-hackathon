import os
from apiclient.discovery import build
import logging
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
# ロガーを設定
logger = logging.getLogger(__name__)

def get_recipe_from_youtube(query: str) -> list[str]:
    """
    検索クエリに関連するYouTube動画のURLを取得する関数
    
    Args:
        query (str): 検索クエリ
    
    Returns:
        list: 動画URLのリスト
    """
    # YouTube API設定
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY environment variable is not set")
    youtube = build("youtube", "v3", developerKey=api_key)
    # 2. 検索して videoId を取得
    try:
        search_response = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            videoCategoryId='26',  # Howto & Style カテゴリ
            maxResults=50  # 1000にすると quota 消費が激しいため初期は50で
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response['items']]
        if not video_ids:
            print("動画が見つかりませんでした。")
            exit()

        # 3. 詳細情報を取得
        videos_response = youtube.videos().list(
            part='contentDetails,statistics,snippet',
            id=','.join(video_ids)
        ).execute()

        # 4. 字幕付き・なしで分類
        videos_with_captions = []
        videos_without_captions = []

        for item in videos_response.get('items', []):
            video_id = item['id']
            title = item['snippet']['title']
            view_count = int(item['statistics'].get('viewCount', 0))
            like_count = int(item['statistics'].get('likeCount', 0))
            caption_flag = item['contentDetails'].get('caption', 'false')  # true or false

            video_info = {
                'title': title,
                'videoId': video_id,
                'views': view_count,
                'likes': like_count,
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }

            if caption_flag == 'true':
                videos_with_captions.append(video_info)
            else:
                videos_without_captions.append(video_info)

        # 5. 字幕あり動画を再生数・高評価順にソート
        videos_with_captions.sort(key=lambda x: (x['views'], x['likes']), reverse=True)
        videos_split_by_caption = [videos_with_captions, videos_without_captions]
        return videos_split_by_caption

    except Exception as e:
        logger.error(f"YouTube APIエラー: {str(e)}")
        return []

