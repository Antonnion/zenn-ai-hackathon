# Python 3.9をベースイメージとして使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt .
COPY app.py .

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポート8080を公開
EXPOSE 8080

# アプリケーションの起動（uvicornを使用）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"] 