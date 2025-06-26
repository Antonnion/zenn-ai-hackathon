from google.cloud import logging as cloud_logging
import logging


def setup_cloud_logging(logger_name: str = "cloud_logger"):
    """
    Cloud Loggingの設定を行う関数
    
    Args:
        logger_name (str): ロガーの名前（デフォルト: "cloud_logger"）
    
    Returns:
        logging.Logger: 設定済みのロガー
    """
    try:
        client = cloud_logging.Client()
        client.setup_logging()
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        return logger
    except Exception as e:
        logging.error(f"Cloud Loggingの設定に失敗しました: {e}")
        return None
        

