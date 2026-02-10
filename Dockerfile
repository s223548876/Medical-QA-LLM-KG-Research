FROM python:3.10-slim

# 安裝系統相依套件（最小化）
RUN apt-get update && apt-get install -y \
    gcc build-essential curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 套件
COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 複製主程式與必要資料
COPY app/main.py ./main.py
COPY app/static ./static
COPY app/models ./models

# 啟動 FastAPI（不使用 reload 模式）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
