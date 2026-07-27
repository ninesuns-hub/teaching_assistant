# 使用轻量级 Python 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 拷贝依赖文件并安装（使用清华大学 PyPI 镜像加速）
COPY requirements.lock .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.lock

# 拷贝后端代码
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app . .
RUN mkdir -p /app/storage && chown -R app:app /app/storage

USER app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "server.py"]
