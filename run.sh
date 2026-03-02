#!/bin/bash
#
# 量化股票监控系统 — 启停管理
# 用法:
#   bash run.sh start    启动全部
#   bash run.sh stop     停止全部
#   bash run.sh restart  重启全部
#   bash run.sh status   查看状态
#   bash run.sh logs     查看后端日志
#

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/env.sh"

PID_DIR="$DIR/.pids"
mkdir -p "$PID_DIR"

start_backend() {
    if [ -f "$PID_DIR/backend.pid" ] && kill -0 "$(cat "$PID_DIR/backend.pid")" 2>/dev/null; then
        echo "后端已在运行 (PID $(cat "$PID_DIR/backend.pid"))"
        return
    fi
    cd "$DIR/backend"
    source venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" > /tmp/quant-backend.log 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
    deactivate
    echo "后端已启动 (PID $!, 端口 $BACKEND_PORT)"
}

start_frontend() {
    if [ -f "$PID_DIR/frontend.pid" ] && kill -0 "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null; then
        echo "前端已在运行 (PID $(cat "$PID_DIR/frontend.pid"))"
        return
    fi
    cd "$DIR/frontend"
    nohup npx serve -s dist -l "$FRONTEND_PORT" > /tmp/quant-frontend.log 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    echo "前端已启动 (PID $!, 端口 $FRONTEND_PORT)"
}

stop_backend() {
    if [ -f "$PID_DIR/backend.pid" ]; then
        PID=$(cat "$PID_DIR/backend.pid")
        kill "$PID" 2>/dev/null && echo "后端已停止 (PID $PID)" || echo "后端未在运行"
        rm -f "$PID_DIR/backend.pid"
    else
        echo "后端未在运行"
    fi
}

stop_frontend() {
    if [ -f "$PID_DIR/frontend.pid" ]; then
        PID=$(cat "$PID_DIR/frontend.pid")
        kill "$PID" 2>/dev/null && echo "前端已停止 (PID $PID)" || echo "前端未在运行"
        rm -f "$PID_DIR/frontend.pid"
    else
        echo "前端未在运行"
    fi
}

show_status() {
    echo ""
    # MySQL
    if docker ps --format '{{.Names}}' | grep -q "^${MYSQL_CONTAINER}$"; then
        echo "  MySQL:  运行中  (容器 $MYSQL_CONTAINER, 端口 $MYSQL_PORT)"
    else
        echo "  MySQL:  已停止"
    fi

    # 后端
    if [ -f "$PID_DIR/backend.pid" ] && kill -0 "$(cat "$PID_DIR/backend.pid")" 2>/dev/null; then
        echo "  后端:   运行中  (PID $(cat "$PID_DIR/backend.pid"), 端口 $BACKEND_PORT)"
    else
        echo "  后端:   已停止"
    fi

    # 前端
    if [ -f "$PID_DIR/frontend.pid" ] && kill -0 "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null; then
        echo "  前端:   运行中  (PID $(cat "$PID_DIR/frontend.pid"), 端口 $FRONTEND_PORT)"
    else
        echo "  前端:   已停止"
    fi
    echo ""
}

case "${1:-help}" in
    start)
        docker start "$MYSQL_CONTAINER" 2>/dev/null || true
        start_backend
        start_frontend
        show_status
        ;;
    stop)
        stop_frontend
        stop_backend
        docker stop "$MYSQL_CONTAINER" 2>/dev/null || true
        echo "全部已停止"
        ;;
    restart)
        stop_frontend
        stop_backend
        sleep 1
        docker start "$MYSQL_CONTAINER" 2>/dev/null || true
        start_backend
        start_frontend
        show_status
        ;;
    status|st)
        show_status
        ;;
    logs|log)
        tail -f /tmp/quant-backend.log
        ;;
    *)
        echo "用法: bash run.sh {start|stop|restart|status|logs}"
        ;;
esac
