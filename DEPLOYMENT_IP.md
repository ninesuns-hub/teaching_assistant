# 阿里云公网 IP 测试部署手册

本文档用于把当前项目部署到一台预装 Docker 的 Ubuntu/Debian 阿里云实例，并通过：

```text
http://服务器公网IP/teaching_assistant/
```

供少量测试用户访问。该入口没有 HTTPS，不应用于真实学生数据或正式全班服务。

## 1. 发布约束

- 服务器只部署主仓库的版本标签。
- 必须使用 `--recurse-submodules`，`backend/agent_core` 按父仓库记录的提交检出。
- 只运行一个后端容器和一个 Uvicorn 进程。
- 不运行多个副本，不共享本地 Qdrant 目录。
- 服务器不直接修改代码。
- 每次更新前先备份 MySQL 和整个 storage。

## 2. 本地发布检查

从项目根目录运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

cd ..\frontend
npm ci
npm run lint
npm run build
```

确认主仓库和子模块状态：

```powershell
git status
git submodule status
```

合并部署准备分支并创建测试版本：

```powershell
git switch main
git pull origin main
git merge --no-ff embedding-4096-deployment
git push origin main
git tag -a v0.1.0-beta.3 -m "4096-dimension IP deployment beta"
git push origin v0.1.0-beta.3
```

只有在审核当前任务的 Changes 并决定保留修改后，才执行上述合并、推送和打标签操作。

## 3. 阿里云安全组

在控制台确认实例具有公网 IPv4，并设置入方向规则：

- TCP 22：来源为管理员公网 IP `/32`
- TCP 80：来源为测试用户公网 IP `/32`
- 不开放 443、8000、3306、6379

如果临时把 80 开放给 `0.0.0.0/0`，测试完成后立即收紧。

## 4. 首次登录和初始化

Windows PowerShell：

```powershell
ssh -i "C:\路径\阿里云密钥.pem" root@服务器公网IP
```

若 root 不可用，尝试 `ubuntu@服务器公网IP`。

服务器检查：

```bash
cat /etc/os-release
docker --version
docker compose version
df -h
free -h
```

当前 2 核 4 GB 实例使用 4096 维向量时，先创建 4 GB swap，降低首次构建和重建索引期间被系统终止的风险：

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
swapon --show
```

如果 `/swapfile` 已存在，不要重复执行上述命令；先运行 `swapon --show` 检查现状。

初始化：

```bash
sudo apt update
sudo apt install -y git rsync curl ufw
sudo adduser deploy
sudo usermod -aG docker deploy

sudo mkdir -p /opt/teaching-assistant/app
sudo mkdir -p /srv/teaching-assistant/{storage,backups,import}
sudo mkdir -p /etc/teaching-assistant
sudo chown -R deploy:deploy /opt/teaching-assistant
sudo chown -R deploy:deploy /srv/teaching-assistant

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
```

退出后重新以 `deploy` 登录，确认 `docker ps` 可运行。

## 5. 克隆发布版本

```bash
cd /opt/teaching-assistant
git clone --recurse-submodules \
  https://github.com/ninesuns-hub/teaching_assistant.git app
cd app
git fetch --tags
git checkout --detach v0.1.0-beta.3
git submodule sync --recursive
git submodule update --init --recursive
git submodule status
```

不要执行 `git submodule update --remote`。

## 6. 生产环境变量

```bash
sudo cp .env.production.example /etc/teaching-assistant/app.env
sudo chown root:deploy /etc/teaching-assistant/app.env
sudo chmod 640 /etc/teaching-assistant/app.env
sudo editor /etc/teaching-assistant/app.env
```

使用 `openssl rand -hex 32` 生成 MySQL、Redis 和 JWT 密钥。必须替换所有 `CHANGE_ME`。

关键配置：

```text
STORAGE_HOST_PATH=/srv/teaching-assistant/storage
MYSQL_HOST=mysql
REDIS_HOST=redis
QDRANT_PATH=/app/storage/processed/vector_db
EMBED_BASE_URL=https://api.siliconflow.cn/v1
EMBED_MODEL_NAME=Qwen/Qwen3-VL-Embedding-8B
EMBED_DIMENSION=4096
EMBED_BATCH_SIZE=32
VISION_BASE_URL=https://api.siliconflow.cn/v1
VISION_MODEL_NAME=Pro/moonshotai/Kimi-K2.6
ALLOWED_ORIGINS=http://服务器公网IP
CHAT_CONTEXT_ENABLED=true
CONVERSATION_SUMMARY_ENABLED=true
MEMORY_WRITE_ENABLED=true
MEMORY_READ_ENABLED=false
```

`EMBED_API_KEY` 和 `VISION_API_KEY` 都填写用户在 SiliconFlow 控制台创建的密钥。示例文件故意将这两个值留空，真实密钥只保存在服务器的 `/etc/teaching-assistant/app.env`，不得提交到 Git。

确保 `/srv/teaching-assistant/storage` 可由后端容器用户写入：

```bash
sudo chown -R 10001:10001 /srv/teaching-assistant/storage
```

## 7. 导出本地数据

停止本地后端并确认没有 queued/running 的学情或记忆任务。

当前 dry run 还发现班级资料记录 `id=3` 对应的
`backend/storage/raw/classes/1/CH2 Propositional Logic.pptx` 缺失。最终导出前应通过教师资料界面重新上传，或从已核验的公共课程原文件恢复到该班级目录，然后重新执行路径 dry run；不得忽略缺失文件继续迁移。

```powershell
mysqldump.exe `
  --single-transaction `
  --routines `
  --triggers `
  --set-gtid-purged=OFF `
  --default-character-set=utf8mb4 `
  --databases Discrete `
  -u root -p `
  --result-file=discrete-production.sql

tar.exe -czf storage-production.tar.gz -C backend storage

Get-FileHash discrete-production.sql -Algorithm SHA256
Get-FileHash storage-production.tar.gz -Algorithm SHA256
```

上传：

```powershell
scp -i "C:\路径\阿里云密钥.pem" `
  discrete-production.sql `
  storage-production.tar.gz `
  deploy@服务器公网IP:/srv/teaching-assistant/import/
```

## 8. 构建基础设施

```bash
cd /opt/teaching-assistant/app

docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml config

docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml build

docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml up -d mysql redis
```

等待 MySQL 和 Redis 健康。

## 9. 导入数据库和文件

```bash
docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml exec -T mysql \
  sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' \
  < /srv/teaching-assistant/import/discrete-production.sql

tar -xzf /srv/teaching-assistant/import/storage-production.tar.gz \
  -C /srv/teaching-assistant

mv /srv/teaching-assistant/storage/processed \
  /srv/teaching-assistant/import/processed-windows-backup

mkdir -p /srv/teaching-assistant/storage/processed/chunks
mkdir -p /srv/teaching-assistant/storage/processed/vector_db
sudo chown -R 10001:10001 /srv/teaching-assistant/storage
```

先做路径 dry run：

```bash
docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml run --rm --no-deps backend \
  python scripts/migrate_storage_paths.py \
  --dry-run --root /app/storage
```

必须为零错误，再把 `--dry-run` 改成 `--apply`。

导入的是当前完整数据库。先标记 baseline，再检查数据库结构与 ORM 元数据没有差异；如果 `alembic check` 报告差异，停止上线并从导入前备份恢复：

```bash
docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml run --rm migrate \
  alembic stamp head

docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml run --rm migrate \
  alembic check
```

重新生成 Linux RAG 索引：

```bash
docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml run --rm --no-deps backend \
  python scripts/ingest_docs.py --rebuild-scoped
```

该命令会删除旧的 1536 维派生索引并按照 `EMBED_DIMENSION=4096` 重新生成；运行期间保持正式后端停止。完成后检查日志中不存在维数不匹配或 Embedding API 错误。

此阶段不要启动正式后端。

## 10. 启动和验收

```bash
docker compose \
  --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml up -d --remove-orphans

docker compose --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml ps
docker compose --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml logs --tail=200 backend

curl http://127.0.0.1/api/health/live
curl http://127.0.0.1/api/health/ready
curl -I http://127.0.0.1/teaching_assistant/
```

浏览器访问：

```text
http://服务器公网IP/teaching_assistant/
```

确认：

- 用户2、班级2、资料20、作业1、附件1
- 会话7、消息18
- 学生报告16、班级反馈3
- 学情任务4且均为 completed
- RAG 文档20、来源40
- 资料和作业下载正常
- SSE聊天、图片、Mermaid、权限隔离正常
- 长期记忆默认关闭
- 公网无法访问8000、3306、6379

## 11. 备份

手动运行：

```bash
cd /opt/teaching-assistant/app
bash scripts/backup.sh
```

脚本会短暂停止后端，备份 MySQL 和整个 storage，生成 SHA-256，并删除超过7天的本机日备份。重要备份还应下载到本地或上传至私有 OSS。

## 12. 更新

创建新标签后：

```bash
cd /opt/teaching-assistant/app
bash scripts/deploy-tag.sh v0.1.0-beta.2
```

脚本会拒绝脏工作树、自动备份、固定子模块版本、运行数据库迁移、重建并检查 readiness。

如果更换 Embedding 模型或向量维度，更新后还必须在后端停止时执行 `ingest_docs.py --rebuild-scoped`。

## 13. 回滚

代码回滚：

```bash
git checkout --detach 上一个版本标签
git submodule update --init --recursive
docker compose --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml build
docker compose --env-file /etc/teaching-assistant/app.env \
  -f compose.production.yml up -d --remove-orphans
```

如果数据库迁移不向后兼容，必须停止服务并恢复同一时间点的 `database.sql` 和 `storage.tar.gz`，不能只回滚代码。
