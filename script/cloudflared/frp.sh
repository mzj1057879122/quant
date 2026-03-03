#!/bin/bash
#
# frp 隧道启停管理
# 用法:
#   bash frp.sh start    启动（frpc + 确保前端）
#   bash frp.sh stop     停止 frpc
#   bash frp.sh restart  重启
#   bash frp.sh status   查看状态
#   bash frp.sh logs     查看 frpc 日志
#
# 首次部署请先执行: bash setup-ec2.sh
#

DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$DIR/../.." && pwd)"
FRPC="$DIR/frpc"
LOG_DIR="$DIR/logs"
PID_DIR="$DIR/.pids"
EC2_IP="18.237.153.223"

start() {
    # 检查后端
    if ! ss -tlnp 2>/dev/null | grep -q ':8072 '; then
        echo "后端(8072)未运行，请先启动"; exit 1
    fi

    # 确保前端
    if ! ss -tlnp 2>/dev/null | grep -q ':8071 '; then
        cd "$PROJECT/frontend"
        nohup npx vite --host 0.0.0.0 --port 8071 > /tmp/quant-frontend.log 2>&1 &
        echo $! > "$PID_DIR/frontend.pid"
        cd "$DIR"
        for i in 1 2 3 4 5 6 7 8 9 10; do
            ss -tlnp 2>/dev/null | grep -q ':8071 ' && break; sleep 1
        done
    fi

    # 确保 EC2 frps
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$EC2_IP \
        'pgrep -f frps > /dev/null || nohup /home/ubuntu/frps -c /home/ubuntu/frps.toml > /home/ubuntu/frps.log 2>&1 &' 2>/dev/null

    # 启动 frpc
    pkill -f "frpc.*frpc.toml" 2>/dev/null || true
    sleep 1
    nohup "$FRPC" -c "$DIR/frpc.toml" > "$LOG_DIR/frpc.log" 2>&1 &
    echo $! > "$PID_DIR/frpc.pid"

    for i in 1 2 3 4 5 6 7 8 9 10; do
        grep -q "start proxy success" "$LOG_DIR/frpc.log" 2>/dev/null && break; sleep 1
    done

    echo ""
    echo "已启动 — http://$EC2_IP:8073"
    echo ""
}

stop() {
    if [ -f "$PID_DIR/frpc.pid" ]; then
        kill "$(cat "$PID_DIR/frpc.pid")" 2>/dev/null
        rm -f "$PID_DIR/frpc.pid"
    fi
    pkill -f "frpc.*frpc.toml" 2>/dev/null || true
    echo "frpc 已停止"
}

status() {
    echo ""
    ss -tlnp 2>/dev/null | grep -q ':8072 ' && echo "  后端:  运行中 (8072)" || echo "  后端:  未运行"
    ss -tlnp 2>/dev/null | grep -q ':8071 ' && echo "  前端:  运行中 (8071)" || echo "  前端:  未运行"
    if [ -f "$PID_DIR/frpc.pid" ] && kill -0 "$(cat "$PID_DIR/frpc.pid")" 2>/dev/null; then
        echo "  frpc:  运行中"
        echo "  地址:  http://$EC2_IP:8073"
    else
        echo "  frpc:  未运行"
    fi
    echo ""
}

case "${1:-help}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  status ;;
    logs)    tail -f "$LOG_DIR/frpc.log" ;;
    *)       echo "用法: bash frp.sh {start|stop|restart|status|logs}" ;;
esac
