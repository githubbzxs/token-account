FROM node:22-slim AS web-build

WORKDIR /app

# 前端依赖单独安装，提升 Docker 构建缓存命中率。
COPY package.json package-lock.json tsconfig.json vite.config.ts ./
COPY web ./web
RUN npm ci && npm run build

FROM python:3.11-slim

WORKDIR /app

# 先安装依赖，提升构建缓存命中率。
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目代码。
COPY . .
COPY --from=web-build /app/web/dist ./web/dist

EXPOSE 8000

CMD ["python", "src/codex_token_report.py", "serve", "--host", "0.0.0.0", "--port", "8000", "--db-file", "/data/token-account.db"]
