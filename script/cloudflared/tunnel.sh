#!/bin/bash
#
# 公网隧道管理（一键启动前端+后端检查+代理+隧道）
#
# 用法:
#   bash tunnel.sh start    启动全部
#   bash tunnel.sh stop     停止全部
#   bash tunnel.sh restart  重启全部
#   bash tunnel.sh status   查看状态
#   bash tunnel.sh logs     查看隧道日志
#

DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$DIR/../.." && pwd)"
PID_DIR="$DIR/.pids"
LOG_DIR="$DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

CLOUDFLARED="$DIR/cloudflared"
PROXY_PORT=8090
FRONTEND_PORT=8071
BACKEND_PORT=8072

# ========== 前端管理 ==========
ensure_frontend() {
    if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT} "; then
        echo "[OK] 前端已在运行 (端口 $FRONTEND_PORT)"
        return
    fi
    echo "[..] 启动前端..."
    cd "$PROJECT_DIR/frontend"
    nohup npx vite --host 0.0.0.0 --port $FRONTEND_PORT > /tmp/quant-frontend.log 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    # 等待端口就绪
    for i in $(seq 1 10); do
        if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT} "; then
            echo "[OK] 前端已启动 (PID $!, 端口 $FRONTEND_PORT)"
            return
        fi
        sleep 1
    done
    echo "[!!] 前端启动失败，查看 /tmp/quant-frontend.log"
    exit 1
}

# ========== 后端检查 ==========
check_backend() {
    if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
        echo "[OK] 后端已在运行 (端口 $BACKEND_PORT)"
    else
        echo "[!!] 后端未运行 (端口 $BACKEND_PORT)，请先启动后端"
        exit 1
    fi
}

# ========== 代理 ==========
start_proxy() {
    # 先杀旧的
    if [ -f "$PID_DIR/proxy.pid" ]; then
        kill "$(cat "$PID_DIR/proxy.pid")" 2>/dev/null
        rm -f "$PID_DIR/proxy.pid"
    fi
    pkill -f "node.*$DIR/proxy.js" 2>/dev/null
    sleep 1
    nohup node "$DIR/proxy.js" > "$LOG_DIR/proxy.log" 2>&1 &
    echo $! > "$PID_DIR/proxy.pid"
    # 等待端口就绪
    for i in $(seq 1 5); do
        if ss -tlnp 2>/dev/null | grep -q ":${PROXY_PORT} "; then
            echo "[OK] 代理已启动 (PID $!, 端口 $PROXY_PORT)"
            return
        fi
        sleep 1
    done
    echo "[!!] 代理启动失败"
    exit 1
}

# ========== 隧道 ==========
start_tunnel() {
    # 先杀旧的
    if [ -f "$PID_DIR/tunnel.pid" ]; then
        kill "$(cat "$PID_DIR/tunnel.pid")" 2>/dev/null
        rm -f "$PID_DIR/tunnel.pid"
    fi
    pkill -f "cloudflared.*tunnel" 2>/dev/null
    sleep 1
    nohup "$CLOUDFLARED" tunnel --url "http://localhost:$PROXY_PORT" --no-autoupdate > "$LOG_DIR/tunnel.log" 2>&1 &
    echo $! > "$PID_DIR/tunnel.pid"
    # 等待公网地址
    for i in $(seq 1 20); do
        URL=$(grep -o 'https://[^ ]*trycloudflare.com' "$LOG_DIR/tunnel.log" 2>/dev/null | head -1)
        if [ -n "$URL" ]; then
            echo "[OK] 隧道已建立"
            echo ""
            echo "============================================"
            echo "  公网地址: $URL"
            echo "============================================"
            echo ""
            # 验证
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$URL")
            API_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$URL/api/v1/stocks")
            echo "  前端验证: HTTP $HTTP_CODE"
            echo "  后端验证: HTTP $API_CODE"
            echo ""
            return
        fi
        sleep 1
    done
    echo "[!!] 隧道建立超时，查看日志: cat $LOG_DIR/tunnel.log"
}

# ========== 全部启动 ==========
start_all() {
    echo "===== 1/4 检查后端 ====="
    check_backend
    echo "===== 2/4 启动前端 ====="
    ensure_frontend
    echo "===== 3/4 启动代理 ====="
    start_proxy
    echo "===== 4/4 启动隧道 ====="
    start_tunnel
}

# ========== 全部停止 ==========
stop_all() {
    for name in tunnel proxy frontend; do
        if [ -f "$PID_DIR/${name}.pid" ]; then
            PID=$(cat "$PID_DIR/${name}.pid")
            kill "$PID" 2>/dev/null
            rm -f "$PID_DIR/${name}.pid"
        fi
    done
    pkill -f "cloudflared.*tunnel" 2>/dev/null
    pkill -f "node.*$DIR/proxy.js" 2>/dev/null
    echo "全部已停止（后端不受影响）"
}

# ========== 状态 ==========
show_status() {
    echo ""
    # 后端
    if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
        echo "  后端:  运行中 (端口 $BACKEND_PORT)"
    else
        echo "  后端:  未运行"
    fi
    # 前端
    if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT} "; then
        echo "  前端:  运行中 (端口 $FRONTEND_PORT)"
    else
        echo "  前端:  未运行"
    fi
    # 代理
    if [ -f "$PID_DIR/proxy.pid" ] && kill -0 "$(cat "$PID_DIR/proxy.pid")" 2>/dev/null; then
        echo "  代理:  运行中 (端口 $PROXY_PORT)"
    else
        echo "  代理:  未运行"
    fi
    # 隧道
    if [ -f "$PID_DIR/tunnel.pid" ] && kill -0 "$(cat "$PID_DIR/tunnel.pid")" 2>/dev/null; then
        URL=$(grep -o 'https://[^ ]*trycloudflare.com' "$LOG_DIR/tunnel.log" 2>/dev/null | head -1)
        echo "  隧道:  运行中"
        [ -n "$URL" ] && echo "  地址:  $URL"
    else
        echo "  隧道:  未运行"
    fi
    echo ""
}

# ========== 主入口 ==========
case "${1:-help}" in
    start)   start_all ;;
    stop)    stop_all ;;
    restart) stop_all; sleep 2; start_all ;;
    status)  show_status ;;
    logs)    tail -f "$LOG_DIR/tunnel.log" ;;
    *)       echo "用法: bash tunnel.sh {start|stop|restart|status|logs}" ;;
esac
