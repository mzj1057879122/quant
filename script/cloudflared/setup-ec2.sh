#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$DIR/../.." && pwd)"
FRPC="$DIR/frpc"
LOG_DIR="$DIR/logs"
PID_DIR="$DIR/.pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

EC2_IP="18.237.153.223"
EC2_SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$EC2_IP"
FRP_TOKEN="quant2024secret"

echo "=========================================="
echo " 一键部署 frp 公网隧道"
echo "=========================================="

# ---------- 1. 检查本地服务 ----------
echo ""
echo "[1/5] 检查本地服务"

if ! ss -tlnp 2>/dev/null | grep -q ':8072 '; then
    echo "  后端(8072)未运行，请先启动后端"
    exit 1
fi
echo "  后端(8072) OK"

if ! ss -tlnp 2>/dev/null | grep -q ':8071 '; then
    echo "  前端(8071)未运行，启动中..."
    cd "$PROJECT/frontend"
    nohup npx vite --host 0.0.0.0 --port 8071 > /tmp/quant-frontend.log 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    cd "$DIR"
    for i in 1 2 3 4 5 6 7 8 9 10; do
        ss -tlnp 2>/dev/null | grep -q ':8071 ' && break
        sleep 1
    done
fi
echo "  前端(8071) OK"

# ---------- 2. EC2 安装并启动 frps ----------
echo ""
echo "[2/5] 配置 EC2 frps"

$EC2_SSH 'bash -s' << 'REMOTE'
set -e
cd /home/ubuntu

if [ ! -f frps ]; then
    curl -sL https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz | tar -xz -C /tmp
    cp /tmp/frp_0.61.1_linux_amd64/frps .
    chmod +x frps
    rm -rf /tmp/frp*
fi

cat > frps.toml << 'C'
bindPort = 7000
auth.token = "quant2024secret"
vhostHTTPPort = 8073
C

pkill -f frps 2>/dev/null || true
sleep 1
nohup ./frps -c frps.toml > frps.log 2>&1 &
sleep 2

if ss -tlnp | grep -q ':7000 '; then
    echo "  frps OK"
else
    echo "  frps FAILED"
    cat frps.log
    exit 1
fi
REMOTE

# ---------- 3. 开放安全组端口 ----------
echo ""
echo "[3/5] 开放 EC2 安全组端口"

for sg in sg-0704787a8c75b2f3e sg-0697f6396a801eba7; do
    for port in 7000 8073; do
        aws ec2 authorize-security-group-ingress --profile zejian.ma --region us-west-2 \
            --group-id "$sg" --protocol tcp --port "$port" --cidr 0.0.0.0/0 2>/dev/null || true
    done
done
echo "  安全组 OK"

# ---------- 4. 本地启动 frpc ----------
echo ""
echo "[4/5] 启动本地 frpc"

cat > "$DIR/frpc.toml" << EOF
serverAddr = "$EC2_IP"
serverPort = 7000
auth.token = "$FRP_TOKEN"

[[proxies]]
name = "quant-web"
type = "http"
localIP = "127.0.0.1"
localPort = 8071
customDomains = ["$EC2_IP"]

[[proxies]]
name = "quant-api"
type = "http"
localIP = "127.0.0.1"
localPort = 8072
customDomains = ["$EC2_IP"]
locations = ["/api"]
EOF

pkill -f "frpc.*frpc.toml" 2>/dev/null || true
sleep 1
nohup "$FRPC" -c "$DIR/frpc.toml" > "$LOG_DIR/frpc.log" 2>&1 &
echo $! > "$PID_DIR/frpc.pid"

for i in 1 2 3 4 5 6 7 8 9 10; do
    if grep -q "start proxy success" "$LOG_DIR/frpc.log" 2>/dev/null; then
        echo "  frpc OK"
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "  frpc 日志:"
        cat "$LOG_DIR/frpc.log"
        exit 1
    fi
    sleep 1
done

# ---------- 5. 验证 ----------
echo ""
echo "[5/5] 验证公网访问"

sleep 2
FE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "http://$EC2_IP:8073" 2>/dev/null || echo "000")
BE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "http://$EC2_IP:8073/api/v1/stocks" 2>/dev/null || echo "000")
echo "  前端: HTTP $FE"
echo "  后端: HTTP $BE"

echo ""
echo "=========================================="
echo "  公网地址: http://$EC2_IP:8073"
echo "=========================================="
echo ""
