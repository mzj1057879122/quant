#!/bin/bash
#
# Sealos 公网隧道 — 一键启停
#
# 原理: SSH保持连接让Devbox进程存活 + frp做数据隧道
#   内网frpc → SSH本地转发:7000 → Devbox:frps:7000
#   公网用户 → Devbox:proxy:8000 → frps:9071/9072 → frp通道 → 内网:8071/8072
#
# 用法:
#   bash sealos.sh start
#   bash sealos.sh stop
#   bash sealos.sh restart
#   bash sealos.sh status
#

DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$DIR/.pids"
LOG_DIR="$DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

SSH_KEY="$DIR/../../frp/bja.sealos.run_ns-1wpzyo2e_devbox-layer0-2"
SSH_HOST="devbox@bja.sealos.run"
SSH_PORT=2233
SSH_OPTS="-i $SSH_KEY -p $SSH_PORT -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3"

FRPC="$DIR/frpc"
FRONTEND_PORT=8071
BACKEND_PORT=8072

# ========== 启动 ==========
start_all() {
    echo "===== 检查本地服务 ====="
    for port in $FRONTEND_PORT $BACKEND_PORT; do
        if ! ss -tlnp 2>/dev/null | grep -q ":${port} "; then
            if [ "$port" = "$FRONTEND_PORT" ]; then
                echo "[..] 前端未运行，启动中..."
                cd "$DIR/../../frontend"
                nohup npx vite --host 0.0.0.0 --port $FRONTEND_PORT > /tmp/quant-frontend.log 2>&1 &
                echo $! > "$PID_DIR/frontend.pid"
                cd "$DIR"
                for i in $(seq 1 10); do
                    ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT} " && break
                    sleep 1
                done
            else
                echo "[!!] 后端未运行 (端口 $port)，请先启动后端"; exit 1
            fi
        fi
        echo "[OK] 端口 $port 正常"
    done

    echo "===== 上传配置到 Devbox ====="
    # frps 配置
    cat > /tmp/frps.toml << 'CONF'
bindPort = 7000
auth.token = "quant2024secret"
CONF

    # proxy.js
    cat > /tmp/proxy.js << 'JSEOF'
const http = require("http");
http.createServer((req, res) => {
  const port = req.url.startsWith("/api") ? 9072 : 9071;
  const p = http.request({hostname:"127.0.0.1",port,path:req.url,method:req.method,headers:req.headers}, r => {
    res.writeHead(r.statusCode, r.headers); r.pipe(res);
  });
  p.on("error", e => { res.writeHead(502); res.end("502: "+e.message); });
  req.pipe(p);
}).listen(8000, "0.0.0.0", () => console.log("proxy ready on :8000"));
JSEOF

    scp $SSH_OPTS /tmp/frps.toml ${SSH_HOST}:/home/devbox/frps.toml 2>/dev/null
    scp $SSH_OPTS /tmp/proxy.js ${SSH_HOST}:/home/devbox/proxy.js 2>/dev/null
    echo "[OK] 配置已上传"

    echo "===== 启动 SSH 长连接 (frps + proxy + 端口转发) ====="
    # 杀旧连接
    [ -f "$PID_DIR/ssh.pid" ] && kill "$(cat "$PID_DIR/ssh.pid")" 2>/dev/null
    pkill -f "ssh.*-L 7000.*bja.sealos.run" 2>/dev/null
    sleep 1

    # SSH 长连接: 跑 frps + proxy 在 Devbox 上，同时 -L 转发 7000 端口
    nohup ssh $SSH_OPTS \
        -L 7000:127.0.0.1:7000 \
        $SSH_HOST \
        'pkill -f frps 2>/dev/null; pkill -f "node.*proxy" 2>/dev/null; sleep 1; /home/devbox/frps -c /home/devbox/frps.toml > /home/devbox/frps.log 2>&1 & node /home/devbox/proxy.js > /home/devbox/proxy.log 2>&1 & wait' \
        > "$LOG_DIR/ssh.log" 2>&1 &
    echo $! > "$PID_DIR/ssh.pid"

    # 等 frps 端口转发就绪
    echo "[..] 等待 frps 就绪..."
    for i in $(seq 1 15); do
        if nc -z 127.0.0.1 7000 2>/dev/null; then
            echo "[OK] frps 就绪 (本地:7000 → Devbox:7000)"
            break
        fi
        [ "$i" -eq 15 ] && { echo "[!!] frps 超时"; cat "$LOG_DIR/ssh.log"; exit 1; }
        sleep 1
    done

    echo "===== 启动 frpc ====="
    [ -f "$PID_DIR/frpc.pid" ] && kill "$(cat "$PID_DIR/frpc.pid")" 2>/dev/null
    pkill -f "frpc.*frpc.toml" 2>/dev/null
    sleep 1

    # frpc 配置
    cat > "$DIR/frpc.toml" << CONF
serverAddr = "127.0.0.1"
serverPort = 7000
auth.token = "quant2024secret"

[[proxies]]
name = "quant-frontend"
type = "tcp"
localIP = "127.0.0.1"
localPort = $FRONTEND_PORT
remotePort = 9071

[[proxies]]
name = "quant-backend"
type = "tcp"
localIP = "127.0.0.1"
localPort = $BACKEND_PORT
remotePort = 9072
CONF

    nohup "$FRPC" -c "$DIR/frpc.toml" > "$LOG_DIR/frpc.log" 2>&1 &
    echo $! > "$PID_DIR/frpc.pid"

    # 等 frpc 注册完成
    for i in $(seq 1 10); do
        if grep -q "start proxy success" "$LOG_DIR/frpc.log" 2>/dev/null; then
            echo "[OK] frpc 注册成功"
            break
        fi
        [ "$i" -eq 10 ] && { echo "[!!] frpc 注册超时"; cat "$LOG_DIR/frpc.log"; exit 1; }
        sleep 1
    done

    echo ""
    echo "============================================"
    echo "  公网地址: https://yothdzjkfukd.sealosbja.site"
    echo "============================================"
    echo ""

    # 验证
    echo "===== 验证 ====="
    ssh $SSH_OPTS $SSH_HOST \
        "FE=\$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1:8000 2>/dev/null); \
         BE=\$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1:8000/api/v1/stocks 2>/dev/null); \
         echo \"  前端: HTTP \$FE\"; echo \"  后端: HTTP \$BE\""
    echo ""
}

# ========== 停止 ==========
stop_all() {
    [ -f "$PID_DIR/frpc.pid" ] && kill "$(cat "$PID_DIR/frpc.pid")" 2>/dev/null && rm -f "$PID_DIR/frpc.pid"
    [ -f "$PID_DIR/ssh.pid" ] && kill "$(cat "$PID_DIR/ssh.pid")" 2>/dev/null && rm -f "$PID_DIR/ssh.pid"
    [ -f "$PID_DIR/frontend.pid" ] && kill "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null && rm -f "$PID_DIR/frontend.pid"
    pkill -f "frpc.*frpc.toml" 2>/dev/null
    pkill -f "ssh.*-L 7000.*bja.sealos.run" 2>/dev/null
    echo "已停止（后端不受影响）"
}

# ========== 状态 ==========
show_status() {
    echo ""
    for pair in "后端:$BACKEND_PORT" "前端:$FRONTEND_PORT"; do
        name="${pair%%:*}"; port="${pair##*:}"
        if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
            echo "  $name:    运行中 (端口 $port)"
        else
            echo "  $name:    未运行"
        fi
    done
    if [ -f "$PID_DIR/ssh.pid" ] && kill -0 "$(cat "$PID_DIR/ssh.pid")" 2>/dev/null; then
        echo "  SSH隧道: 运行中"
    else
        echo "  SSH隧道: 未运行"
    fi
    if [ -f "$PID_DIR/frpc.pid" ] && kill -0 "$(cat "$PID_DIR/frpc.pid")" 2>/dev/null; then
        echo "  frpc:    运行中"
    else
        echo "  frpc:    未运行"
    fi
    echo ""
}

case "${1:-help}" in
    start)   start_all ;;
    stop)    stop_all ;;
    restart) stop_all; sleep 2; start_all ;;
    status)  show_status ;;
    logs)    tail -f "$LOG_DIR/frpc.log" ;;
    *)       echo "用法: bash sealos.sh {start|stop|restart|status|logs}" ;;
esac
