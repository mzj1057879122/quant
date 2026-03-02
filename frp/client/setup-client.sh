#!/bin/bash
# 内网服务器一键部署 frpc
# 用法: bash setup-client.sh

set -e

FRP_VERSION="0.61.1"
ARCH="amd64"

# 检查是否修改了公网 IP
if grep -q "你的公网IP" frpc.toml; then
    echo "请先修改 frpc.toml 中的 serverAddr 为你的公网服务器 IP"
    exit 1
fi

# 下载 frp
if [ ! -f frpc ]; then
    echo "下载 frp v${FRP_VERSION}..."
    curl -L -o frp.tar.gz "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_${ARCH}.tar.gz"
    tar -xzf frp.tar.gz
    cp "frp_${FRP_VERSION}_linux_${ARCH}/frpc" .
    rm -rf "frp_${FRP_VERSION}_linux_${ARCH}" frp.tar.gz
    chmod +x frpc
fi

# 停掉旧进程
pkill frpc 2>/dev/null || true
sleep 1

# 启动
nohup ./frpc -c frpc.toml > frpc.log 2>&1 &
echo "frpc 已启动 (PID $!)"
echo "穿透建立完成，公网访问地址: http://$(grep serverAddr frpc.toml | head -1 | awk -F'\"' '{print $2}'):8073"
