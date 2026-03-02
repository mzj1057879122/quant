#!/bin/bash
#
# 量化股票监控系统 — 首次部署脚本（只跑一次）
# 用法: bash deploy.sh
#

set -e

# ============ 修改这里 ============
MYSQL_PASSWORD="your_password_here"    # ← 务必修改
SERVER_CHAN_KEY=""                      # Server酱 Key（可选）
MYSQL_DATA_DIR="/data/mysql8"          # MySQL 数据持久化目录
# ==================================

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/env.sh"

echo "===== 1. 环境检查 ====="
for cmd in docker python3 npm node; do
    command -v $cmd &>/dev/null || { echo "$cmd 未安装"; exit 1; }
done
echo "Python: $(python3 --version) | Node: $(node -v) | Docker: $(docker -v)"

echo "===== 2. MySQL ====="
if docker ps -a --format '{{.Names}}' | grep -q "^${MYSQL_CONTAINER}$"; then
    docker start "$MYSQL_CONTAINER" 2>/dev/null || true
    echo "MySQL 容器已存在"
else
    mkdir -p "$MYSQL_DATA_DIR"
    docker run -d --name "$MYSQL_CONTAINER" --restart always \
        -p "${MYSQL_PORT}:3306" \
        -v "${MYSQL_DATA_DIR}:/var/lib/mysql" \
        -e MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD" \
        -e MYSQL_DATABASE="$DB_NAME" \
        mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    echo "等待 MySQL 就绪..."
    for i in $(seq 1 30); do
        docker exec "$MYSQL_CONTAINER" mysqladmin ping -h127.0.0.1 -uroot -p"$MYSQL_PASSWORD" --silent 2>/dev/null && break
        [ "$i" -eq 30 ] && { echo "MySQL 超时"; exit 1; }
        sleep 2
    done
fi
echo "MySQL OK"

echo "===== 3. 后端依赖 ====="
cd "$DIR/backend"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

cat > .env << EOF
DB_HOST=127.0.0.1
DB_PORT=${MYSQL_PORT}
DB_USER=root
DB_PASSWORD=${MYSQL_PASSWORD}
DB_NAME=${DB_NAME}
SERVER_CHAN_KEY=${SERVER_CHAN_KEY}
EOF

echo "执行数据库迁移..."
alembic upgrade head
deactivate
echo "后端 OK"

echo "===== 4. 前端构建 ====="
cd "$DIR/frontend"
npm install --silent
npm run build
echo "前端 OK"

echo ""
echo "===== 部署完成 ====="
echo "启动: bash run.sh start"
echo "状态: bash run.sh status"
