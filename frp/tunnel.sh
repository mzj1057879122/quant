#!/bin/bash
#
# 一键建立隧道（在内网服务器执行）
# 用法:
#   bash tunnel.sh start   启动隧道
#   bash tunnel.sh stop    停止隧道
#   bash tunnel.sh status  查看状态
#

DIR="$(cd "$(dirname "$0")" && pwd)"
SSH_KEY="$DIR/bja.sealos.run_ns-1wpzyo2e_devbox-layer0-2"
SSH_HOST="devbox@bja.sealos.run"
SSH_PORT=2233
PID_FILE="$DIR/.tunnel.pid"

start_tunnel() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "隧道已在运行 (PID $(cat "$PID_FILE"))"
        return
    fi

    echo "1. 上传代理脚本到 Devbox..."
    scp -i "$SSH_KEY" -P $SSH_PORT -o StrictHostKeyChecking=no "$DIR/proxy.js" ${SSH_HOST}:/home/devbox/proxy.js

    echo "2. 启动 Devbox 上的代理服务..."
    ssh -i "$SSH_KEY" -p $SSH_PORT -o StrictHostKeyChecking=no $SSH_HOST \
        "pkill -f 'node.*proxy.js' 2>/dev/null; sleep 1; nohup node /home/devbox/proxy.js > /home/devbox/proxy.log 2>&1 &"

    echo "3. 建立 SSH 反向隧道..."
    # -R 9071:127.0.0.1:8071  Devbox:9071 → 内网:8071 (前端)
    # -R 9072:127.0.0.1:8072  Devbox:9072 → 内网:8072 (后端)
    ssh -i "$SSH_KEY" -p $SSH_PORT -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -N -f \
        -R 9071:127.0.0.1:8071 \
        -R 9072:127.0.0.1:8072 \
        $SSH_HOST

    echo $! > "$PID_FILE"
    # ssh -f 后台后拿不到准确 pid，用 pgrep 找
    pgrep -f "ssh.*-R 9071.*bja.sealos.run" > "$PID_FILE"

    echo ""
    echo "隧道已建立！访问地址: https://yothdzjkfukd.sealosbja.site"
    echo ""
}

stop_tunnel() {
    # 杀本地 SSH 隧道
    pkill -f "ssh.*-R 9071.*bja.sealos.run" 2>/dev/null
    rm -f "$PID_FILE"

    # 杀 Devbox 上的代理
    ssh -i "$SSH_KEY" -p $SSH_PORT -o StrictHostKeyChecking=no $SSH_HOST \
        "pkill -f 'node.*proxy.js' 2>/dev/null" 2>/dev/null

    echo "隧道已关闭"
}

show_status() {
    if pgrep -f "ssh.*-R 9071.*bja.sealos.run" > /dev/null 2>&1; then
        echo "隧道: 运行中 (PID $(pgrep -f 'ssh.*-R 9071.*bja.sealos.run'))"
        echo "访问: https://yothdzjkfukd.sealosbja.site"
    else
        echo "隧道: 未运行"
    fi
}

case "${1:-help}" in
    start)   start_tunnel ;;
    stop)    stop_tunnel ;;
    restart) stop_tunnel; sleep 1; start_tunnel ;;
    status)  show_status ;;
    *)       echo "用法: bash tunnel.sh {start|stop|restart|status}" ;;
esac
