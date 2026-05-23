FROM python:3.11-slim

WORKDIR /app

# 先安装依赖，提升构建缓存命中率。
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目代码。
COPY . .

EXPOSE 8000

CMD ["python", "src/codex_token_report.py", "serve", "--host", "0.0.0.0", "--port", "8000", "--db-file", "/data/token-account.db"]
