# --- 构建阶段 ---
FROM node:20-alpine AS build-stage

WORKDIR /app

# 安装依赖（增加重试机制和超时时间）
COPY package*.json ./
RUN npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm install --registry=https://registry.npmmirror.com

# 拷贝源码并构建
COPY . .
RUN npm run build

# --- 生产阶段 ---
FROM nginx:stable-alpine AS production-stage

# 拷贝构建后的文件到 Nginx 目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 拷贝自定义 Nginx 配置（可选，处理单页应用路由）
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
