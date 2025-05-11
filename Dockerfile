# Python 3.9をベースイメージとして使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt .
COPY app.py .
COPY .env .

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポート3000を公開
EXPOSE 3000

# アプリケーションの起動（uvicornを使用）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"] 