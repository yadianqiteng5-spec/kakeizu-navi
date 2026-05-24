FROM python:3.11-slim

# システム依存（最小限）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存パッケージを先にインストール（レイヤキャッシュ最適化）
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリ本体
COPY . .

# 不要ファイルが入っていてもキャッシュ汚染を防ぐ
RUN rm -rf .git .github .pytest_cache __pycache__ 2>/dev/null || true

EXPOSE 8501

# Streamlit のヘルスチェックエンドポイント
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

# 本番起動コマンド
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true", \
     "--browser.gatherUsageStats=false"]
